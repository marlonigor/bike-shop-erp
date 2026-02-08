from django.shortcuts import render, get_object_or_404, redirect
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


def stock_adjust(request):
    """Realiza ajuste manual de estoque para quantidade exata."""
    from .forms import StockAdjustmentForm
    
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            warehouse = form.cleaned_data['warehouse']
            new_quantity = form.cleaned_data['new_quantity']
            reason = form.cleaned_data['reason']
            
            try:
                StockService.adjust_stock(
                    product=product,
                    warehouse=warehouse,
                    new_quantity=new_quantity,
                    reason=reason
                )
                if request.headers.get('HX-Request'):
                    return HttpResponse(status=204, headers={'HX-Trigger': 'stockListChanged'})
                return redirect('stock:stock_list')
            except Exception as e:
                # Retorna erro para o frontend (pode ser melhorado com mensagens)
                form.add_error(None, str(e))
    else:
        form = StockAdjustmentForm()
    
    return render(request, 'stock/stock_adjust.html', {'form': form})


def stock_history(request):
    """Lista histórico de movimentações de estoque."""
    from .models import StockMovement
    
    movements = StockMovement.objects.select_related('product', 'warehouse').order_by('-created_at')
    
    # Filtros simples
    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)
        
    movement_type = request.GET.get('type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
        
    # Paginação simples (limite 50)
    movements = movements[:50]
    
    context = {
        'movements': movements,
        'selected_product': product_id,
        'selected_type': movement_type,
    }
    
    return render(request, 'stock/stock_history.html', context)
