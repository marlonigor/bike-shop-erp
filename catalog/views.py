"""Controladores web para gestao do catalogo de produtos, categorias e marcas."""

from decimal import Decimal
from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BrandForm, CategoryForm, ProductForm
from .models import Brand, Category, Product


def product_list(request: HttpRequest) -> HttpResponse:
    """Lista todos os produtos ativos com filtros por categoria e busca textual."""
    products: QuerySet[Product] = Product.objects.select_related('category', 'brand').order_by('name')
    categories = list(Category.objects.all())

    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category_id=category_filter)

    for cat in categories:
        cat.is_selected = str(cat.id) == category_filter

    search = request.GET.get('q')
    if search:
        products = products.filter(name__icontains=search) | products.filter(sku__icontains=search)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_filter,
        'search': search or '',
    }

    if request.headers.get('HX-Request'):
        return render(request, 'catalog/partials/product_table.html', context)
    return render(request, 'catalog/product_list.html', context)


def product_create(request: HttpRequest) -> HttpResponse:
    """Cria um novo produto via formulario padrao ou requisicao HTMX."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'productListChanged'})
            return redirect('catalog:product_list')
    else:
        form = ProductForm()

    return render(request, 'catalog/product_form.html', {'form': form})


def product_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Atualiza dados cadastrais de um produto existente."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'productListChanged'})
            return redirect('catalog:product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'catalog/product_form.html', {'product': product, 'form': form})


def product_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Desativa logicamente um produto do catalogo."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product.active = False
        product.save()
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'productListChanged'})
        return redirect('catalog:product_list')

    return render(request, 'catalog/product_confirm_delete.html', {'product': product})


def _build_product_metrics(product: Product) -> dict[str, Any]:
    """Calcula indicadores financeiros e operacionais consolidados do produto."""
    from sales.models import SaleItem
    from stock.models import Stock

    margin = ((product.price - product.cost) / product.price * 100) if product.price > 0 else Decimal('0.00')
    stock_by_warehouse = list(Stock.objects.filter(product=product).select_related('warehouse'))
    sales_history = list(
        SaleItem.objects.filter(product=product)
        .select_related('sale', 'sale__client')
        .order_by('-created_at')[:10]
    )

    return {
        'product': product,
        'margin': margin,
        'stock_by_warehouse': stock_by_warehouse,
        'total_stock': sum(s.quantity for s in stock_by_warehouse),
        'sales_history': sales_history,
        'total_sold': sum(item.quantity for item in sales_history),
        'total_revenue': sum(item.total_price for item in sales_history),
    }


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Exibe indicadores consolidados e historico de movimentacao do produto."""
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), pk=pk)
    context = _build_product_metrics(product)
    return render(request, 'catalog/product_detail.html', context)


# ============================================
# Categoria CRUD
# ============================================

def category_list(request: HttpRequest) -> HttpResponse:
    """Lista todas as categorias cadastradas."""
    return render(request, 'catalog/category_list.html', {'categories': Category.objects.all()})


def category_create(request: HttpRequest) -> HttpResponse:
    """Cadastra uma nova categoria no sistema."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'categoryListChanged'})
            return redirect('catalog:category_list')
    else:
        form = CategoryForm()

    return render(request, 'catalog/category_form.html', {'form': form})


def category_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita uma categoria existente."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'categoryListChanged'})
            return redirect('catalog:category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'catalog/category_form.html', {'form': form, 'category': category})


def category_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove uma categoria do sistema."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'categoryListChanged'})
        return redirect('catalog:category_list')

    return render(request, 'catalog/category_confirm_delete.html', {'category': category})


# ============================================
# Marca CRUD
# ============================================

def brand_list(request: HttpRequest) -> HttpResponse:
    """Lista todas as marcas cadastradas."""
    return render(request, 'catalog/brand_list.html', {'brands': Brand.objects.all()})


def brand_create(request: HttpRequest) -> HttpResponse:
    """Cadastra uma nova marca."""
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'brandListChanged'})
            return redirect('catalog:brand_list')
    else:
        form = BrandForm()

    return render(request, 'catalog/brand_form.html', {'form': form})


def brand_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita dados cadastrais de uma marca."""
    brand = get_object_or_404(Brand, pk=pk)

    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'brandListChanged'})
            return redirect('catalog:brand_list')
    else:
        form = BrandForm(instance=brand)

    return render(request, 'catalog/brand_form.html', {'form': form, 'brand': brand})


def brand_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove uma marca do sistema."""
    brand = get_object_or_404(Brand, pk=pk)

    if request.method == 'POST':
        brand.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'brandListChanged'})
        return redirect('catalog:brand_list')

    return render(request, 'catalog/brand_confirm_delete.html', {'brand': brand})
