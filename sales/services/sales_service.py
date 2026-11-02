"""
SalesService - Serviço para gestão de vendas e integração com estoque.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from core.exceptions import InvalidStatusTransitionError
from customers.models import Customer
from sales.models import Sale, SaleItem
from stock.models import StockMovement, Warehouse
from stock.services import StockService

if TYPE_CHECKING:
    from services.models import ServiceOrder


def _copy_order_items_to_sale(sale: Sale, order: 'ServiceOrder') -> None:
    """Copia os itens e servicos da OS para a venda formalizada."""
    for item in order.items.select_related('product'):
        SaleItem.objects.create(
            sale=sale,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
        )


def _validate_order_for_invoicing(order: 'ServiceOrder') -> None:
    """Valida se a OS esta em condicoes operacionais para emissao de venda."""
    if order.status not in {'COMPLETED', 'DELIVERED'}:
        raise InvalidStatusTransitionError(
            model_name='ServiceOrder',
            current_status=order.status,
            target_status='DELIVERED',
            allowed={'COMPLETED', 'DELIVERED'},
        )
    if hasattr(order, 'sale') and order.sale is not None:
        raise ValueError(f'A OS {order.id} ja possui faturamento na Venda {order.sale.id}.')


class SalesService:
    """
    Serviço para gerenciar o fluxo de vendas.
    """

    @staticmethod
    @transaction.atomic
    def create_sale(
        customer: Customer, warehouse: Warehouse, items_data: list[dict], notes: str = ''
    ) -> Sale:
        """
        Cria uma venda e realiza a baixa de estoque para cada item físico.

        items_data deve ser uma lista de dicionários:
        [
            {'product': product_obj, 'quantity': 10, 'unit_price': Decimal('50.00')},
            ...
        ]
        """
        # 1. Criar o cabeçalho da venda
        sale = Sale.objects.create(
            customer=customer, warehouse=warehouse, notes=notes, status=Sale.Status.COMPLETED
        )

        total_sale_amount = Decimal('0.00')

        # 2. Processar itens e baixar estoque
        for item in items_data:
            product = item['product']
            quantity = item['quantity']
            unit_price = item['unit_price']

            # Calcular preço total do item
            item_total = unit_price * quantity
            total_sale_amount += item_total

            # Criar o item da venda
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                total_price=item_total,
            )

            # Baixar estoque via StockService apenas para produtos fisicos (nao servicos)
            # Se não houver estoque, o StockService levantará InsufficientStockError
            # e a transação atômica fará o rollback de toda a venda.
            if not product.is_service:
                StockService.remove_stock(
                    product=product,
                    warehouse=warehouse,
                    quantity=quantity,
                    reference_type=StockMovement.ReferenceType.SALE,
                    reference_id=sale.id,
                    reason=f'Venda {sale.id}',
                )

        # 3. Atualizar o total da venda
        sale.total_amount = total_sale_amount
        sale.save()

        return sale

    @staticmethod
    @transaction.atomic
    def create_sale_from_service_order(order: 'ServiceOrder', notes: str = '') -> Sale:
        """Gera uma venda formal no PDV a partir de uma OS sem duplicar baixa de estoque."""
        _validate_order_for_invoicing(order)
        default_notes = notes or f'Faturamento referente a OS {str(order.id)[:8]}'
        sale = Sale.objects.create(
            customer=order.customer,
            warehouse=order.warehouse,
            service_order=order,
            total_amount=order.total_amount,
            status=Sale.Status.COMPLETED,
            notes=default_notes,
        )
        _copy_order_items_to_sale(sale, order)
        if order.status == 'COMPLETED':
            order.change_status('DELIVERED')
        return sale
