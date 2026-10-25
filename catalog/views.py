import json
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BrandForm, CategoryForm, ProductForm
from .models import Brand, Category, Product


def _hx_or_redirect(
    request: HttpRequest, trigger: str, redirect_to: str, message: str | None = None
) -> HttpResponse:
    """Retorna 204 com trigger para HTMX ou redireciona a navegacao padrao com mensagem."""
    if message:
        messages.success(request, message)
    if request.headers.get('HX-Request'):
        payload: dict[str, Any] = {trigger: True}
        if message:
            payload['showToast'] = {'message': message, 'type': 'success'}
        return HttpResponse(status=204, headers={'HX-Trigger': json.dumps(payload)})
    return redirect(redirect_to)


def _filter_products(
    request: HttpRequest,
) -> tuple[QuerySet[Product], list[Category], str | None, str]:
    """Aplica filtros de categoria e busca textual na listagem de produtos."""
    products: QuerySet[Product] = Product.objects.select_related('category', 'brand').order_by(
        'name'
    )
    categories = list(Category.objects.all())
    cat_filter = request.GET.get('category')
    if cat_filter:
        products = products.filter(category_id=cat_filter)
    for cat in categories:
        cat.is_selected = str(cat.id) == cat_filter
    search = request.GET.get('q') or ''
    if search:
        products = products.filter(name__icontains=search) | products.filter(sku__icontains=search)
    return products, categories, cat_filter, search


def product_list(request: HttpRequest) -> HttpResponse:
    """Lista produtos ativos com suporte a filtros e renderizacao parcial HTMX."""
    products, categories, cat_filter, search = _filter_products(request)
    context = {
        'products': products,
        'categories': categories,
        'selected_category': cat_filter,
        'search': search,
    }
    template = (
        'catalog/partials/product_table.html'
        if request.headers.get('HX-Request')
        else 'catalog/product_list.html'
    )
    return render(request, template, context)


def product_create(request: HttpRequest) -> HttpResponse:
    """Cria um novo produto via formulario padrao ou requisicao HTMX."""
    if request.method != 'POST':
        return render(request, 'catalog/product_form.html', {'form': ProductForm()})

    form = ProductForm(request.POST)
    if not form.is_valid():
        return render(request, 'catalog/product_form.html', {'form': form})

    product = form.save()
    msg = f"Produto '{product.name}' cadastrado com sucesso!"
    return _hx_or_redirect(request, 'productListChanged', 'catalog:product_list', message=msg)


def product_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Atualiza dados cadastrais de um produto existente."""
    product = get_object_or_404(Product, pk=pk)
    if request.method != 'POST':
        form = ProductForm(instance=product)
        return render(request, 'catalog/product_form.html', {'product': product, 'form': form})

    form = ProductForm(request.POST, instance=product)
    if not form.is_valid():
        return render(request, 'catalog/product_form.html', {'product': product, 'form': form})

    product = form.save()
    msg = f"Produto '{product.name}' atualizado com sucesso!"
    return _hx_or_redirect(request, 'productListChanged', 'catalog:product_list', message=msg)


def product_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Desativa logicamente um produto do catalogo."""
    product = get_object_or_404(Product, pk=pk)
    if request.method != 'POST':
        return render(request, 'catalog/product_confirm_delete.html', {'product': product})

    product.active = False
    product.save()
    msg = f"Produto '{product.name}' desativado com sucesso."
    return _hx_or_redirect(request, 'productListChanged', 'catalog:product_list', message=msg)


def _build_product_metrics(product: Product) -> dict[str, Any]:
    """Calcula indicadores financeiros e operacionais consolidados do produto."""
    from sales.models import SaleItem
    from stock.models import Stock

    margin = (
        ((product.price - product.cost) / product.price * 100)
        if product.price > 0
        else Decimal('0.00')
    )
    stock_by_wh = list(Stock.objects.filter(product=product).select_related('warehouse'))
    sales_history = list(
        SaleItem.objects.filter(product=product)
        .select_related('sale', 'sale__customer')
        .order_by('-created_at')[:10]
    )
    return {
        'product': product,
        'margin': margin,
        'stock_by_warehouse': stock_by_wh,
        'total_stock': sum(s.quantity for s in stock_by_wh),
        'sales_history': sales_history,
        'total_sold': sum(item.quantity for item in sales_history),
        'total_revenue': sum(item.total_price for item in sales_history),
    }


def product_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Exibe indicadores consolidados e historico de movimentacao do produto."""
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), pk=pk)
    return render(request, 'catalog/product_detail.html', _build_product_metrics(product))


def category_list(request: HttpRequest) -> HttpResponse:
    """Lista todas as categorias com suporte a renderizacao parcial para HTMX."""
    context = {'categories': Category.objects.all()}
    template = (
        'catalog/partials/category_table.html'
        if request.headers.get('HX-Request')
        else 'catalog/category_list.html'
    )
    return render(request, template, context)


def category_create(request: HttpRequest) -> HttpResponse:
    """Cadastra uma nova categoria no sistema."""
    if request.method != 'POST':
        return render(request, 'catalog/category_form.html', {'form': CategoryForm()})

    form = CategoryForm(request.POST)
    if not form.is_valid():
        return render(request, 'catalog/category_form.html', {'form': form})

    category = form.save()
    msg = f"Categoria '{category.name}' cadastrada com sucesso!"
    return _hx_or_redirect(request, 'categoryListChanged', 'catalog:category_list', message=msg)


def category_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita uma categoria existente."""
    category = get_object_or_404(Category, pk=pk)
    if request.method != 'POST':
        form = CategoryForm(instance=category)
        return render(request, 'catalog/category_form.html', {'form': form, 'category': category})

    form = CategoryForm(request.POST, instance=category)
    if not form.is_valid():
        return render(request, 'catalog/category_form.html', {'form': form, 'category': category})

    category = form.save()
    msg = f"Categoria '{category.name}' atualizada com sucesso!"
    return _hx_or_redirect(request, 'categoryListChanged', 'catalog:category_list', message=msg)


def category_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove uma categoria do sistema."""
    category = get_object_or_404(Category, pk=pk)
    if request.method != 'POST':
        return render(request, 'catalog/category_confirm_delete.html', {'category': category})

    category.delete()
    msg = f"Categoria '{category.name}' removida com sucesso."
    return _hx_or_redirect(request, 'categoryListChanged', 'catalog:category_list', message=msg)


def brand_list(request: HttpRequest) -> HttpResponse:
    """Lista todas as marcas cadastradas com suporte a HTMX."""
    context = {'brands': Brand.objects.all()}
    template = (
        'catalog/partials/brand_table.html'
        if request.headers.get('HX-Request')
        else 'catalog/brand_list.html'
    )
    return render(request, template, context)


def brand_create(request: HttpRequest) -> HttpResponse:
    """Cadastra uma nova marca."""
    if request.method != 'POST':
        return render(request, 'catalog/brand_form.html', {'form': BrandForm()})

    form = BrandForm(request.POST)
    if not form.is_valid():
        return render(request, 'catalog/brand_form.html', {'form': form})

    brand = form.save()
    msg = f"Marca '{brand.name}' cadastrada com sucesso!"
    return _hx_or_redirect(request, 'brandListChanged', 'catalog:brand_list', message=msg)


def brand_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita dados cadastrais de uma marca."""
    brand = get_object_or_404(Brand, pk=pk)
    if request.method != 'POST':
        form = BrandForm(instance=brand)
        return render(request, 'catalog/brand_form.html', {'form': form, 'brand': brand})

    form = BrandForm(request.POST, instance=brand)
    if not form.is_valid():
        return render(request, 'catalog/brand_form.html', {'form': form, 'brand': brand})

    brand = form.save()
    msg = f"Marca '{brand.name}' atualizada com sucesso!"
    return _hx_or_redirect(request, 'brandListChanged', 'catalog:brand_list', message=msg)


def brand_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove uma marca do sistema."""
    brand = get_object_or_404(Brand, pk=pk)
    if request.method != 'POST':
        return render(request, 'catalog/brand_confirm_delete.html', {'brand': brand})

    brand.delete()
    msg = f"Marca '{brand.name}' removida com sucesso."
    return _hx_or_redirect(request, 'brandListChanged', 'catalog:brand_list', message=msg)
