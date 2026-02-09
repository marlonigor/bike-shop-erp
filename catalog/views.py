from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Product, Category


def product_list(request):
    """Lista todos os produtos."""
    products = Product.objects.select_related('category', 'brand').order_by('name')
    categories = Category.objects.all()
    
    # Filtro por categoria
    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Busca por nome/SKU
    search = request.GET.get('q')
    if search:
        products = products.filter(name__icontains=search) | products.filter(sku__icontains=search)
    
    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_filter,
        'search': search or '',
    }
    
    # Se for requisição HTMX, retorna apenas a tabela
    if request.headers.get('HX-Request'):
        return render(request, 'catalog/partials/product_table.html', context)
    
    return render(request, 'catalog/product_list_v2.html', context)


def product_create(request):
    """Cria um novo produto."""
    from .forms import ProductForm
    
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


def product_edit(request, pk):
    """Edita um produto existente."""
    from .forms import ProductForm
    
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
    
    return render(request, 'catalog/product_form.html', {
        'product': product,
        'form': form,
    })


def product_delete(request, pk):
    """Exclui um produto."""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product.active = False
        product.save()
        
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'productListChanged'})
        return redirect('catalog:product_list')
    
    return render(request, 'catalog/product_confirm_delete.html', {'product': product})


def product_detail(request, pk):
    """Exibe detalhes completos de um produto."""
    from stock.models import Stock
    from sales.models import SaleItem
    from decimal import Decimal
    
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), pk=pk)
    
    # Calcular margem de lucro
    if product.price > 0:
        margin = ((product.price - product.cost) / product.price) * 100
    else:
        margin = Decimal('0.00')
    
    # Estoque por depósito
    stock_by_warehouse = Stock.objects.filter(product=product).select_related('warehouse')
    total_stock = sum(s.quantity for s in stock_by_warehouse)
    
    # Histórico de vendas (últimas 10)
    sales_history = SaleItem.objects.filter(
        product=product
    ).select_related('sale', 'sale__client').order_by('-created_at')[:10]
    
    # Total vendido
    total_sold = sum(item.quantity for item in sales_history)
    total_revenue = sum(item.total_price for item in sales_history)
    
    context = {
        'product': product,
        'margin': margin,
        'stock_by_warehouse': stock_by_warehouse,
        'total_stock': total_stock,
        'sales_history': sales_history,
        'total_sold': total_sold,
        'total_revenue': total_revenue,
    }
    
    return render(request, 'catalog/product_detail.html', context)


# ============================================
# Category CRUD
# ============================================

def category_list(request):
    """Lista todas as categorias."""
    categories = Category.objects.all()
    return render(request, 'catalog/category_list.html', {'categories': categories})


def category_create(request):
    """Cria uma nova categoria."""
    from .forms import CategoryForm
    
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


def category_edit(request, pk):
    """Edita uma categoria existente."""
    from .forms import CategoryForm
    
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


def category_delete(request, pk):
    """Exclui uma categoria."""
    from .models import Brand
    
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        category.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'categoryListChanged'})
        return redirect('catalog:category_list')
    
    return render(request, 'catalog/category_confirm_delete.html', {'category': category})


# ============================================
# Brand CRUD
# ============================================

def brand_list(request):
    """Lista todas as marcas."""
    from .models import Brand
    
    brands = Brand.objects.all()
    return render(request, 'catalog/brand_list.html', {'brands': brands})


def brand_create(request):
    """Cria uma nova marca."""
    from .forms import BrandForm
    
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


def brand_edit(request, pk):
    """Edita uma marca existente."""
    from .forms import BrandForm
    from .models import Brand
    
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


def brand_delete(request, pk):
    """Exclui uma marca."""
    from .models import Brand
    
    brand = get_object_or_404(Brand, pk=pk)
    
    if request.method == 'POST':
        brand.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'brandListChanged'})
        return redirect('catalog:brand_list')
    
    return render(request, 'catalog/brand_confirm_delete.html', {'brand': brand})

