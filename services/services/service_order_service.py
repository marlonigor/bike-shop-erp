"""
ServiceOrderService - Camada de servico centralizada para o ciclo de vida da oficina mecanica.
Encapsula abertura, adicao de pecas/servicos, aprovacao e baixa de estoque de pecas aplicadas.
"""

import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction

from catalog.models import Product
from customers.models import Customer
from services.models import ServiceOrder, ServiceOrderItem
from stock.models import StockMovement, Warehouse
from stock.services import StockService


def _deduct_order_stock(order: ServiceOrder) -> None:
    """Realiza a baixa de estoque de todas as pecas fisicas aplicadas na OS."""
    for item in order.items.select_related('product'):
        if not item.product.is_service:
            StockService.remove_stock(
                product=item.product,
                warehouse=order.warehouse,
                quantity=item.quantity,
                reference_type=StockMovement.ReferenceType.SERVICE_ORDER,
                reference_id=order.id,
                reason=f'Baixa de peca na OS {order.id}',
            )


def _restore_order_stock(order: ServiceOrder) -> None:
    """Estorna as pecas fisicas para o estoque caso a OS concluida seja cancelada."""
    for item in order.items.select_related('product'):
        if not item.product.is_service:
            StockService.add_stock(
                product=item.product,
                warehouse=order.warehouse,
                quantity=item.quantity,
                reference_type=StockMovement.ReferenceType.SERVICE_ORDER,
                reference_id=order.id,
                reason=f'Estorno por cancelamento da OS {order.id}',
            )


class ServiceOrderService:
    """Servico responsavel pelas operacoes e regras de negocio de Ordens de Servico."""

    @staticmethod
    @transaction.atomic
    def create_order(
        customer: Customer,
        warehouse: Warehouse,
        bike_description: str,
        client_reported_defect: str,
        mechanic: User | None = None,
        bike_serial_number: str = '',
        accessories_left: str = '',
        notes: str = '',
    ) -> ServiceOrder:
        """Abre uma nova Ordem de Servico no status inicial DRAFT (Orcamento)."""
        return ServiceOrder.objects.create(
            customer=customer,
            warehouse=warehouse,
            bike_description=bike_description,
            client_reported_defect=client_reported_defect,
            mechanic=mechanic,
            bike_serial_number=bike_serial_number,
            accessories_left=accessories_left,
            notes=notes,
            status=ServiceOrder.Status.DRAFT,
        )

    @staticmethod
    @transaction.atomic
    def add_item(
        order: ServiceOrder,
        product: Product,
        quantity: int,
        unit_price: Decimal | None = None,
        notes: str = '',
    ) -> ServiceOrderItem:
        """Adiciona um item (peca ou servico) a OS e recalcula totais."""
        if quantity <= 0:
            raise ValueError(
                f'Quantidade invalida: recebido {quantity}, esperado numero inteiro maior que zero.'
            )

        locked_order = ServiceOrder.objects.select_for_update().get(id=order.id)
        if locked_order.status in {
            ServiceOrder.Status.COMPLETED,
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CANCELLED,
        }:
            raise ValueError(
                f'Operacao negada: nao e permitido adicionar itens a uma OS no status {locked_order.status}.'
            )

        price = unit_price if unit_price is not None else product.price
        item = ServiceOrderItem.objects.create(
            service_order=locked_order,
            product=product,
            quantity=quantity,
            unit_price=price,
            total_price=price * quantity,
            notes=notes,
        )
        locked_order.recalculate_totals()
        return item

    @staticmethod
    @transaction.atomic
    def remove_item(order: ServiceOrder, item_id: uuid.UUID) -> None:
        """Remove um item da OS e recalcula totais financeiros."""
        locked_order = ServiceOrder.objects.select_for_update().get(id=order.id)
        if locked_order.status in {
            ServiceOrder.Status.COMPLETED,
            ServiceOrder.Status.DELIVERED,
            ServiceOrder.Status.CANCELLED,
        }:
            raise ValueError(
                f'Operacao negada: nao e permitido remover itens de uma OS no status {locked_order.status}.'
            )

        item = ServiceOrderItem.objects.get(service_order=locked_order, id=item_id)
        item.delete()
        locked_order.recalculate_totals()

    @staticmethod
    @transaction.atomic
    def approve_order(order: ServiceOrder) -> ServiceOrder:
        """Aprova o orcamento da OS para permitir inicio da execucao tecnica."""
        locked_order = ServiceOrder.objects.select_for_update().get(id=order.id)
        locked_order.change_status(ServiceOrder.Status.APPROVED)
        return locked_order

    @staticmethod
    @transaction.atomic
    def start_maintenance(order: ServiceOrder) -> ServiceOrder:
        """Inicia a execucao dos servicos na bancada da oficina."""
        locked_order = ServiceOrder.objects.select_for_update().get(id=order.id)
        locked_order.change_status(ServiceOrder.Status.IN_PROGRESS)
        return locked_order

    @staticmethod
    @transaction.atomic
    def complete_order(order: ServiceOrder) -> ServiceOrder:
        """
        Conclui os servicos da OS e realiza a baixa das pecas fisicas no estoque.
        Servicos imateriais (mao de obra) nao sofrem baixa.
        """
        locked_order = ServiceOrder.objects.select_for_update().get(id=order.id)
        locked_order.change_status(ServiceOrder.Status.COMPLETED)
        _deduct_order_stock(locked_order)
        return locked_order

    @staticmethod
    @transaction.atomic
    def deliver_order(order: ServiceOrder) -> ServiceOrder:
        """Registra a entrega da bicicleta revisada ao cliente."""
        locked_order = ServiceOrder.objects.select_for_update().get(id=order.id)
        locked_order.change_status(ServiceOrder.Status.DELIVERED)
        return locked_order

    @staticmethod
    @transaction.atomic
    def cancel_order(order: ServiceOrder) -> ServiceOrder:
        """
        Cancela a Ordem de Servico. Se as pecas ja haviam sido baixadas (status COMPLETED),
        executa estorno automatico das quantidades no deposito correspondente.
        """
        locked_order = ServiceOrder.objects.select_for_update().get(id=order.id)
        previous_status = locked_order.status
        locked_order.change_status(ServiceOrder.Status.CANCELLED)

        if previous_status == ServiceOrder.Status.COMPLETED:
            _restore_order_stock(locked_order)
        return locked_order
