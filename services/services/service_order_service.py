"""
ServiceOrderService - Camada de servico centralizada para o ciclo de vida da oficina mecanica.
Encapsula abertura, adicao de pecas/servicos, aprovacao e baixa de estoque de pecas aplicadas.
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction

from catalog.models import Product
from customers.models import Customer
from services.models import ServiceOrder, ServiceOrderItem
from stock.models import StockMovement, Warehouse
from stock.services import StockService


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
            raise ValueError('A quantidade do item deve ser maior que zero.')

        price = unit_price if unit_price is not None else product.price

        item = ServiceOrderItem.objects.create(
            service_order=order,
            product=product,
            quantity=quantity,
            unit_price=price,
            total_price=price * quantity,
            notes=notes,
        )
        order.recalculate_totals()
        return item

    @staticmethod
    @transaction.atomic
    def remove_item(order: ServiceOrder, item_id) -> None:
        """Remove um item da OS e recalcula totais financeiros."""
        item = ServiceOrderItem.objects.get(service_order=order, id=item_id)
        item.delete()
        order.recalculate_totals()

    @staticmethod
    @transaction.atomic
    def approve_order(order: ServiceOrder) -> ServiceOrder:
        """Aprova o orcamento da OS para permitir inicio da execucao tecnica."""
        order.change_status(ServiceOrder.Status.APPROVED)
        return order

    @staticmethod
    @transaction.atomic
    def start_maintenance(order: ServiceOrder) -> ServiceOrder:
        """Inicia a execucao dos servicos na bancada da oficina."""
        order.change_status(ServiceOrder.Status.IN_PROGRESS)
        return order

    @staticmethod
    @transaction.atomic
    def complete_order(order: ServiceOrder) -> ServiceOrder:
        """
        Conclui os servicos da OS e realiza a baixa das pecas fisicas no estoque.
        Servicos imateriais (mao de obra) nao sofrem baixa.
        """
        order.change_status(ServiceOrder.Status.COMPLETED)

        # Baixa de estoque para cada peca aplicada
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
        return order

    @staticmethod
    @transaction.atomic
    def deliver_order(order: ServiceOrder) -> ServiceOrder:
        """Registra a entrega da bicicleta revisada ao cliente."""
        order.change_status(ServiceOrder.Status.DELIVERED)
        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order: ServiceOrder) -> ServiceOrder:
        """
        Cancela a Ordem de Servico. Se as pecas ja haviam sido baixadas (status COMPLETED),
        executa estorno automatico das quantidades no deposito correspondente.
        """
        previous_status = order.status
        order.change_status(ServiceOrder.Status.CANCELLED)

        # Se ja havia sido concluida, devolve as pecas para o estoque
        if previous_status == ServiceOrder.Status.COMPLETED:
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
        return order
