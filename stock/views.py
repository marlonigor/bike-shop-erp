from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from .models import Stock, Warehouse
from .services import StockService
from catalog.models import Product


def stock_list(request):
    """Lista todo o estoque."""
    stocks = Stock.objects.select_related('product', 'warehouse').order_by('product__name')
    warehouses = Warehouse.objects.all()
    
    # Filtro por depósito
    warehouse_filter = request.GET.get('warehouse')
    if warehouse_filter:
        stocks = stocks.filter(warehouse_id=warehouse_filter)
    
    # Filtro por baixo estoque
    low_stock = request.GET.get('low_stock')
    if low_stock:
        stocks = stocks.filter(quantity__lt=10)
    
    context = {
        'stocks': stocks,
        'warehouses': warehouses,
        'selected_warehouse': warehouse_filter,
        'low_stock': low_stock,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'stock/partials/stock_table.html', context)
    
    return render(request, 'stock/stock_list.html', context)


def stock_movement(request):
    """Registra movimentação de estoque."""
    products = Product.objects.filter(active=True)
    warehouses = Warehouse.objects.all()
    
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=request.POST['product_id'])
        warehouse = get_object_or_404(Warehouse, pk=request.POST['warehouse_id'])
        quantity = int(request.POST['quantity'])
        movement_type = request.POST['movement_type']
        reason = request.POST.get('reason', '')
        
        try:
            if movement_type == 'IN':
                StockService.add_stock(product, warehouse, quantity, reason=reason)
            else:
                StockService.remove_stock(product, warehouse, quantity, reason=reason)
            
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'stockListChanged'})
        except Exception as e:
            return HttpResponse(f'Erro: {str(e)}', status=400)
    
    return render(request, 'stock/stock_movement.html', {
        'products': products,
        'warehouses': warehouses,
    })
