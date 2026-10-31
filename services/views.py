"""Controladores web para o modulo de Ordens de Servico e Oficina Mecanica."""

import json
import uuid

from django.contrib import messages
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.exceptions import InsufficientStockError, InvalidStatusTransitionError

from .forms import ServiceOrderForm, ServiceOrderItemForm
from .models import ServiceOrder
from .services import ServiceOrderService


def _filter_orders(request: HttpRequest) -> tuple[QuerySet[ServiceOrder], str, str]:
    """Aplica filtros por status e busca textual na listagem de Ordens de Servico."""
    orders = ServiceOrder.objects.select_related('customer', 'warehouse', 'mechanic')
    status_filter = request.GET.get('status', '').strip().upper()
    if status_filter and status_filter != 'ALL':
        orders = orders.filter(status=status_filter)

    search = request.GET.get('q', '').strip()
    if search:
        orders = orders.filter(
            Q(customer__name__icontains=search)
            | Q(bike_description__icontains=search)
            | Q(bike_serial_number__icontains=search)
        )
    return orders, status_filter, search


def service_order_list(request: HttpRequest) -> HttpResponse:
    """Exibe a listagem gerencial de Ordens de Servico com filtros por status."""
    orders, status_filter, search = _filter_orders(request)
    context = {
        'orders': orders,
        'selected_status': status_filter,
        'search': search,
        'status_choices': ServiceOrder.Status.choices,
    }
    template_name = (
        'services/partials/order_table.html'
        if request.headers.get('HX-Request')
        else 'services/service_order_list.html'
    )
    return render(request, template_name, context)


def service_order_create(request: HttpRequest) -> HttpResponse:
    """Abre uma nova Ordem de Servico via formulario com status inicial DRAFT."""
    if request.method != 'POST':
        return render(request, 'services/service_order_form.html', {'form': ServiceOrderForm()})

    form = ServiceOrderForm(request.POST)
    if not form.is_valid():
        return render(request, 'services/service_order_form.html', {'form': form})

    order = form.save()
    messages.success(request, f'Ordem de Serviço OS-{str(order.id)[:8]} aberta com sucesso!')
    return redirect('services:service_order_detail', pk=order.id)


def service_order_detail(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Exibe a visao consolidada da OS com pecas, servicos e painel de status."""
    order = get_object_or_404(
        ServiceOrder.objects.select_related('customer', 'warehouse', 'mechanic'),
        pk=pk,
    )
    context = {
        'order': order,
        'items': order.items.select_related('product'),
        'item_form': ServiceOrderItemForm(),
        'allowed_transitions': order.VALID_TRANSITIONS.get(order.status, set()),
    }
    return render(request, 'services/service_order_detail.html', context)


def _render_items_response(
    request: HttpRequest, order: ServiceOrder, toast_message: str
) -> HttpResponse:
    """Renderiza a partial com a tabela de itens e cabecalho HX-Trigger."""
    order.refresh_from_db()
    context = {'order': order, 'items': order.items.select_related('product')}
    payload = {'showToast': {'message': toast_message, 'type': 'success'}}
    response = render(request, 'services/partials/order_items_table.html', context)
    response['HX-Trigger'] = json.dumps(payload)
    return response


def service_order_add_item(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Endpoint HTMX para adicionar peca ou mao de obra a Ordem de Servico."""
    order = get_object_or_404(ServiceOrder, pk=pk)
    if request.method != 'POST':
        return HttpResponse(status=405)

    form = ServiceOrderItemForm(request.POST)
    if not form.is_valid():
        return HttpResponse('Dados do item inválidos.', status=400)

    ServiceOrderService.add_item(
        order=order,
        product=form.cleaned_data['product'],
        quantity=form.cleaned_data['quantity'],
        unit_price=form.cleaned_data.get('unit_price'),
        notes=form.cleaned_data.get('notes', ''),
    )
    return _render_items_response(request, order, 'Item adicionado à OS!')


def service_order_remove_item(
    request: HttpRequest, pk: uuid.UUID, item_id: uuid.UUID
) -> HttpResponse:
    """Endpoint HTMX para remover item da OS e atualizar os totais."""
    order = get_object_or_404(ServiceOrder, pk=pk)
    if request.method != 'POST':
        return HttpResponse(status=405)

    ServiceOrderService.remove_item(order, item_id)
    return _render_items_response(request, order, 'Item removido da OS.')


def _apply_status_action(order: ServiceOrder, target_status: str) -> None:
    """Despacha a transicao para o metodo correspondente no ServiceOrderService."""
    match target_status:
        case ServiceOrder.Status.APPROVED:
            ServiceOrderService.approve_order(order)
        case ServiceOrder.Status.IN_PROGRESS:
            ServiceOrderService.start_maintenance(order)
        case ServiceOrder.Status.COMPLETED:
            ServiceOrderService.complete_order(order)
        case ServiceOrder.Status.DELIVERED:
            ServiceOrderService.deliver_order(order)
        case ServiceOrder.Status.CANCELLED:
            ServiceOrderService.cancel_order(order)
        case _:
            order.change_status(target_status)


def service_order_change_status(
    request: HttpRequest, pk: uuid.UUID, target_status: str
) -> HttpResponse:
    """Executa a transicao de status da OS e baixa/estorna estoque quando aplicavel."""
    order = get_object_or_404(ServiceOrder, pk=pk)
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        _apply_status_action(order, target_status)
        messages.success(request, f'Status alterado para {order.get_status_display()}!')
    except (InvalidStatusTransitionError, InsufficientStockError) as e:
        messages.error(request, str(e))

    return redirect('services:service_order_detail', pk=order.id)
