from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from decimal import Decimal

from catalog.models import Product
from stock.models import Warehouse
from core.models import Client
from .services import SalesService
from stock.services import StockService


def pdv(request):
    """Tela principal do PDV."""
    warehouses = Warehouse.objects.all()
    clients = Client.objects.all()
    
    # Carrinho na sessão
    cart = request.session.get('cart', [])
    cart_total = sum(Decimal(str(item['total'])) for item in cart)
    
    context = {
        'warehouses': warehouses,
        'clients': clients,
        'cart': cart,
        'cart_total': cart_total,
    }
    return render(request, 'sales/pdv.html', context)


def product_search(request):
    """Busca produtos para adicionar ao carrinho (HTMX)."""
    query = request.GET.get('q', '')
    warehouse_id = request.GET.get('warehouse')
    
    products = Product.objects.filter(active=True)
    
    if query:
        products = products.filter(name__icontains=query) | products.filter(sku__icontains=query)
    
    products = products[:10]
    
    # Adicionar info de estoque
    results = []
    for product in products:
        stock = 0
        if warehouse_id:
            stock = StockService.get_balance(product, Warehouse.objects.get(id=warehouse_id))
        results.append({
            'product': product,
            'stock': stock,
        })
    
    return render(request, 'sales/partials/product_search_results.html', {'results': results})


def cart_add(request):
    """Adiciona item ao carrinho (HTMX)."""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        product = get_object_or_404(Product, pk=product_id)
        
        cart = request.session.get('cart', [])
        
        # Verifica se já existe no carrinho
        for item in cart:
            if item['product_id'] == str(product.id):
                item['quantity'] += quantity
                item['total'] = str(Decimal(item['unit_price']) * item['quantity'])
                break
        else:
            cart.append({
                'product_id': str(product.id),
                'sku': product.sku,
                'name': product.name,
                'quantity': quantity,
                'unit_price': str(product.price),
                'total': str(product.price * quantity),
            })
        
        request.session['cart'] = cart
        request.session.modified = True
        
        cart_total = sum(Decimal(item['total']) for item in cart)
        
        return render(request, 'sales/partials/cart_items.html', {
            'cart': cart,
            'cart_total': cart_total,
        })
    
    return HttpResponse(status=400)


def sale_complete(request):
    """Finaliza a venda."""
    if request.method == 'POST':
        cart = request.session.get('cart', [])
        
        if not cart:
            return HttpResponse('Carrinho vazio', status=400)
        
        client_id = request.POST.get('client_id')
        warehouse_id = request.POST.get('warehouse_id')
        
        client = get_object_or_404(Client, pk=client_id)
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
        
        # Montar items_data
        items_data = []
        for item in cart:
            product = Product.objects.get(pk=item['product_id'])
            items_data.append({
                'product': product,
                'quantity': item['quantity'],
                'unit_price': Decimal(item['unit_price']),
            })
        
        try:
            sale = SalesService.create_sale(client, warehouse, items_data)
            
            # Limpar carrinho
            request.session['cart'] = []
            request.session.modified = True
            
            return render(request, 'sales/partials/sale_success.html', {'sale': sale})
        except Exception as e:
            return HttpResponse(f'Erro: {str(e)}', status=400)
    
    return HttpResponse(status=400)
