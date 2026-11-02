from decimal import Decimal

import pytest

from catalog.models import Category, Product
from core.exceptions import InsufficientStockError
from customers.models import Customer
from sales.models import Sale
from sales.services import SalesService
from stock.services import StockService


@pytest.fixture
def customer(db):
    return Customer.objects.create(name='João Silva', document='12345678901')


@pytest.fixture
def client(customer):
    return customer


@pytest.mark.django_db
class TestSalesService:
    def test_create_sale_successful(self, client, warehouse, product):
        """Venda bem-sucedida deve reduzir o estoque e criar registros de venda."""
        # Arrange: Adicionar estoque inicial
        StockService.add_stock(product, warehouse, 10)

        items_data = [{'product': product, 'quantity': 3, 'unit_price': Decimal('100.00')}]

        # Act
        sale = SalesService.create_sale(client, warehouse, items_data)

        # Assert
        assert sale.status == Sale.Status.COMPLETED
        assert sale.total_amount == Decimal('300.00')
        assert sale.items.count() == 1
        assert StockService.get_balance(product, warehouse) == 7

    def test_create_sale_insufficient_stock_raises_error(self, client, warehouse, product):
        """Venda com estoque insuficiente deve levantar erro e não criar venda (rollback)."""
        # Arrange: Estoque insuficiente
        StockService.add_stock(product, warehouse, 2)

        items_data = [{'product': product, 'quantity': 5, 'unit_price': Decimal('100.00')}]

        # Act & Assert
        with pytest.raises(InsufficientStockError):
            SalesService.create_sale(client, warehouse, items_data)

        # Verificar que a venda não foi criada
        assert Sale.objects.count() == 0
        # Verificar que o estoque permaneceu o mesmo
        assert StockService.get_balance(product, warehouse) == 2

    def test_create_sale_multiple_items(self, client, warehouse, product, product_secondary):
        """Venda com múltiplos itens deve processar todos corretamente."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)
        StockService.add_stock(product_secondary, warehouse, 20)

        items_data = [
            {'product': product, 'quantity': 2, 'unit_price': Decimal('50.00')},
            {'product': product_secondary, 'quantity': 5, 'unit_price': Decimal('20.00')},
        ]

        # Act
        sale = SalesService.create_sale(client, warehouse, items_data)

        # Assert
        assert sale.total_amount == Decimal('200.00')  # (2*50) + (5*20)
        assert StockService.get_balance(product, warehouse) == 8
        assert StockService.get_balance(product_secondary, warehouse) == 15

    def test_create_sale_service_item_does_not_deduct_or_require_stock(self, client, warehouse):
        """Venda de servico nao deve baixar estoque nem exigir saldo."""
        cat_service = Category.objects.create(name='Oficina', type=Category.Type.SERVICE)
        service_prod = Product.objects.create(
            name='Revisão Completa',
            sku='REV-COMP',
            price=Decimal('150.00'),
            cost=Decimal('0.00'),
            category=cat_service,
            is_service=True,
        )

        items_data = [{'product': service_prod, 'quantity': 1, 'unit_price': Decimal('150.00')}]

        sale = SalesService.create_sale(client, warehouse, items_data)

        assert sale.status == Sale.Status.COMPLETED
        assert sale.total_amount == Decimal('150.00')
        assert sale.items.count() == 1
        assert StockService.get_balance(service_prod, warehouse) == 0

    def test_create_sale_from_service_order_success(self, customer, warehouse, product):
        """OS concluida deve gerar venda no PDV e transicionar para entregue."""
        from services.models import ServiceOrder, ServiceOrderItem

        order = ServiceOrder.objects.create(
            customer=customer,
            warehouse=warehouse,
            bike_description='Caloi 29',
            status=ServiceOrder.Status.COMPLETED,
        )
        ServiceOrderItem.objects.create(
            service_order=order,
            product=product,
            quantity=2,
            unit_price=Decimal('100.00'),
            total_price=Decimal('200.00'),
        )
        order.recalculate_totals()
        sale = SalesService.create_sale_from_service_order(order)

        assert sale.service_order == order
        assert sale.customer == customer
        assert sale.total_amount == Decimal('200.00')
        assert sale.items.count() == 1
        order.refresh_from_db()
        assert order.status == ServiceOrder.Status.DELIVERED

    def test_create_sale_from_service_order_invalid_status_raises_error(self, customer, warehouse):
        """Tentativa de faturar OS nao concluida deve levantar erro de transicao."""
        from core.exceptions import InvalidStatusTransitionError
        from services.models import ServiceOrder

        order = ServiceOrder.objects.create(
            customer=customer,
            warehouse=warehouse,
            bike_description='Caloi 29',
            status=ServiceOrder.Status.DRAFT,
        )
        with pytest.raises(InvalidStatusTransitionError):
            SalesService.create_sale_from_service_order(order)

    def test_create_sale_from_service_order_already_invoiced_raises_error(
        self, customer, warehouse
    ):
        """OS ja faturada nao pode gerar uma segunda venda."""
        from services.models import ServiceOrder

        order = ServiceOrder.objects.create(
            customer=customer,
            warehouse=warehouse,
            bike_description='Caloi 29',
            status=ServiceOrder.Status.COMPLETED,
        )
        SalesService.create_sale_from_service_order(order)

        with pytest.raises(ValueError, match='ja possui faturamento'):
            SalesService.create_sale_from_service_order(order)
