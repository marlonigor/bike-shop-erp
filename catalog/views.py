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
    
    return render(request, 'catalog/product_list.html', context)


def product_create(request):
    """Cria um novo produto."""
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product = Product.objects.create(
            sku=request.POST['sku'],
            name=request.POST['name'],
            category_id=request.POST['category'],
            cost=request.POST.get('cost', 0),
            price=request.POST['price'],
        )
        
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'productListChanged'})
        return redirect('catalog:product_list')
    
    return render(request, 'catalog/product_form.html', {'categories': categories})


def product_edit(request, pk):
    """Edita um produto existente."""
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product.sku = request.POST['sku']
        product.name = request.POST['name']
        product.category_id = request.POST['category']
        product.cost = request.POST.get('cost', 0)
        product.price = request.POST['price']
        product.save()
        
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'productListChanged'})
        return redirect('catalog:product_list')
    
    return render(request, 'catalog/product_form.html', {
        'product': product,
        'categories': categories,
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
