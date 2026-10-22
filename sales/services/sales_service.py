"""
SalesService - Serviço para gestão de vendas e integração com estoque.
"""

from decimal import Decimal

from django.db import transaction

from core.models import Client
from sales.models import Sale, SaleItem
from stock.models import StockMovement, Warehouse
from stock.services import StockService


class SalesService:
    """
    Serviço para gerenciar o fluxo de vendas.
    """

    @staticmethod
    @transaction.atomic
    def create_sale(
        client: Client, warehouse: Warehouse, items_data: list[dict], notes: str = ''
    ) -> Sale:
        """
        Cria uma venda e realiza a baixa de estoque para cada item.

        items_data deve ser uma lista de dicionários:
        [
            {'product': product_obj, 'quantity': 10, 'unit_price': Decimal('50.00')},
            ...
        ]
        """
        # 1. Criar o cabeçalho da venda
        sale = Sale.objects.create(
            client=client, warehouse=warehouse, notes=notes, status=Sale.Status.COMPLETED
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

            # Baixar estoque via StockService
            # Se não houver estoque, o StockService levantará InsufficientStockError
            # e a transação atômica fará o rollback de toda a venda.
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
