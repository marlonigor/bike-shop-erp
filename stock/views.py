"""Controladores web para gestao e movimentacao de estoque."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Product
from core.exceptions import InsufficientStockError
from .forms import StockAdjustmentForm
from .models import Stock, StockMovement, Warehouse
from .services import StockService


def stock_list(request: HttpRequest) -> HttpResponse:
    """Lista o saldo de estoque com suporte a filtros e atualizacao HTMX."""
    stocks = Stock.objects.select_related('product', 'warehouse').order_by('product__name')
    warehouses = list(Warehouse.objects.all())

    warehouse_filter = request.GET.get('warehouse')
    if warehouse_filter:
        stocks = stocks.filter(warehouse_id=warehouse_filter)

    for wh in warehouses:
        wh.is_selected = str(wh.id) == warehouse_filter

    low_stock = request.GET.get('low_stock')
    if low_stock:
        stocks = stocks.filter(quantity__lt=10)

    context = {
        'stocks': stocks,
        'warehouses': warehouses,
        'selected_warehouse': warehouse_filter,
        'low_stock': low_stock,
    }

    template_name = 'stock/partials/stock_table.html' if request.headers.get('HX-Request') else 'stock/stock_list.html'
    return render(request, template_name, context)


def stock_movement(request: HttpRequest) -> HttpResponse:
    """Processa entrada e saida de mercadorias no estoque."""
    if request.method != 'POST':
        return render(request, 'stock/stock_movement.html', {
            'products': Product.objects.filter(active=True),
            'warehouses': Warehouse.objects.all(),
        })

    product = get_object_or_404(Product, pk=request.POST.get('product_id'))
    warehouse = get_object_or_404(Warehouse, pk=request.POST.get('warehouse_id'))
    quantity = int(request.POST.get('quantity', 0))
    movement_type = request.POST.get('movement_type', '')
    reason = request.POST.get('reason', '')

    try:
        if movement_type == 'IN':
            StockService.add_stock(product, warehouse, quantity, reason=reason)
        else:
            StockService.remove_stock(product, warehouse, quantity, reason=reason)

        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'stockListChanged'})
        return redirect('stock:stock_list')
    except (InsufficientStockError, ValueError) as e:
        return HttpResponse(f'Erro: {str(e)}', status=400)


def stock_adjust(request: HttpRequest) -> HttpResponse:
    """Realiza ajuste manual de inventario para quantidade absoluta."""
    if request.method != 'POST':
        return render(request, 'stock/stock_adjust.html', {'form': StockAdjustmentForm()})

    form = StockAdjustmentForm(request.POST)
    if not form.is_valid():
        return render(request, 'stock/stock_adjust.html', {'form': form})

    try:
        StockService.adjust_stock(
            product=form.cleaned_data['product'],
            warehouse=form.cleaned_data['warehouse'],
            new_quantity=form.cleaned_data['new_quantity'],
            reason=form.cleaned_data['reason'],
        )
        if request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Trigger': 'stockListChanged'})
        return redirect('stock:stock_list')
    except (InsufficientStockError, ValueError) as e:
        form.add_error(None, str(e))
        return render(request, 'stock/stock_adjust.html', {'form': form})


def stock_history(request: HttpRequest) -> HttpResponse:
    """Exibe o historico auditavel das ultimas 50 movimentacoes."""
    movements = StockMovement.objects.select_related('product', 'warehouse').order_by('-created_at')

    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)

    movement_type = request.GET.get('type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)

    context = {
        'movements': movements[:50],
        'selected_product': product_id,
        'selected_type': movement_type,
    }
    return render(request, 'stock/stock_history.html', context)
