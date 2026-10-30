"""Controladores web para gestao e movimentacao de estoque."""

import json
from typing import Any

from django.contrib import messages
from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Product
from core.exceptions import InsufficientStockError

from .forms import StockAdjustmentForm
from .models import Stock, StockMovement, Warehouse
from .services import StockService


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


def _filter_stocks(
    request: HttpRequest,
) -> tuple[QuerySet[Stock], list[Warehouse], str | None, str | None]:
    """Aplica filtros por deposito e alerta de estoque baixo."""
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
    return stocks, warehouses, warehouse_filter, low_stock


def stock_list(request: HttpRequest) -> HttpResponse:
    """Lista o saldo de estoque com suporte a filtros e atualizacao HTMX."""
    stocks, warehouses, wh_filter, low_stock = _filter_stocks(request)
    context = {
        'stocks': stocks,
        'warehouses': warehouses,
        'selected_warehouse': wh_filter,
        'low_stock': low_stock,
    }
    template_name = (
        'stock/partials/stock_table.html'
        if request.headers.get('HX-Request')
        else 'stock/stock_list.html'
    )
    return render(request, template_name, context)


def _execute_movement(
    request: HttpRequest,
) -> tuple[Product, Warehouse, int, str]:
    """Executa adicao ou baixa de estoque a partir dos parametros da requisicao."""
    product = get_object_or_404(Product, pk=request.POST.get('product_id'))
    warehouse = get_object_or_404(Warehouse, pk=request.POST.get('warehouse_id'))
    quantity = int(request.POST.get('quantity', 0))
    movement_type = request.POST.get('movement_type', '')
    reason = request.POST.get('reason', '')
    if movement_type == 'IN':
        StockService.add_stock(product, warehouse, quantity, reason=reason)
    else:
        StockService.remove_stock(product, warehouse, quantity, reason=reason)
    return product, warehouse, quantity, movement_type


def stock_movement(request: HttpRequest) -> HttpResponse:
    """Processa entrada e saida de mercadorias no estoque."""
    if request.method != 'POST':
        context = {
            'products': Product.objects.filter(active=True),
            'warehouses': Warehouse.objects.all(),
        }
        return render(request, 'stock/stock_movement.html', context)
    try:
        product, _, quantity, movement_type = _execute_movement(request)
        action_name = 'Entrada' if movement_type == 'IN' else 'Saída'
        msg = f"{action_name} de {quantity} un do produto '{product.name}' registrada com sucesso!"
        return _hx_or_redirect(request, 'stockListChanged', 'stock:stock_list', message=msg)
    except (InsufficientStockError, ValueError) as e:
        messages.error(request, str(e))
        context = {
            'products': Product.objects.filter(active=True),
            'warehouses': Warehouse.objects.all(),
            'error': str(e),
        }
        return render(request, 'stock/stock_movement.html', context, status=400)


def stock_adjust(request: HttpRequest) -> HttpResponse:
    """Realiza ajuste manual de inventario para quantidade absoluta."""
    if request.method != 'POST':
        return render(request, 'stock/stock_adjust.html', {'form': StockAdjustmentForm()})
    form = StockAdjustmentForm(request.POST)
    if not form.is_valid():
        return render(request, 'stock/stock_adjust.html', {'form': form})
    try:
        product = form.cleaned_data['product']
        new_quantity = form.cleaned_data['new_quantity']
        StockService.adjust_stock(
            product=product,
            warehouse=form.cleaned_data['warehouse'],
            new_quantity=new_quantity,
            reason=form.cleaned_data['reason'],
        )
        msg = f"Estoque de '{product.name}' ajustado para {new_quantity} un com sucesso!"
        return _hx_or_redirect(request, 'stockListChanged', 'stock:stock_list', message=msg)
    except (InsufficientStockError, ValueError) as e:
        form.add_error(None, str(e))
        return render(request, 'stock/stock_adjust.html', {'form': form})


def _filter_movements(request: HttpRequest) -> QuerySet[StockMovement]:
    """Filtra movimentacoes por produto, tipo e intervalo de datas."""
    movements = StockMovement.objects.select_related('product', 'warehouse').order_by('-created_at')
    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)
    movement_type = request.GET.get('type')
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    start_date = request.GET.get('start_date')
    if start_date:
        movements = movements.filter(created_at__date__gte=start_date)
    end_date = request.GET.get('end_date')
    if end_date:
        movements = movements.filter(created_at__date__lte=end_date)
    return movements


def _paginate_movements(request: HttpRequest, movements: QuerySet[StockMovement]) -> Page:
    """Aplica paginacao de 20 registros por pagina nas movimentacoes."""
    paginator = Paginator(movements, 20)
    page_number = request.GET.get('page', '1')
    return paginator.get_page(page_number)


def _build_history_context(request: HttpRequest, page_obj: Page) -> dict[str, object]:
    """Monta o contexto para renderizacao do historico com filtros ativos."""
    selected_prod = request.GET.get('product', '')
    products = list(Product.objects.filter(active=True).order_by('name'))
    for prod in products:
        prod.is_selected = str(prod.id) == selected_prod
    return {
        'page_obj': page_obj,
        'movements': page_obj.object_list,
        'products': products,
        'selected_product': selected_prod,
        'selected_type': request.GET.get('type', ''),
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
        'movement_types': StockMovement.MovementType.choices,
    }


def stock_history(request: HttpRequest) -> HttpResponse:
    """Exibe o historico auditavel com suporte a filtros por periodo e paginacao."""
    movements = _filter_movements(request)
    page_obj = _paginate_movements(request, movements)
    context = _build_history_context(request, page_obj)
    template_name = (
        'stock/partials/history_table.html'
        if request.headers.get('HX-Request')
        else 'stock/stock_history.html'
    )
    return render(request, template_name, context)
