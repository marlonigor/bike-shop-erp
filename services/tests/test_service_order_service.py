from decimal import Decimal

import pytest

from catalog.models import Category, Product
from core.exceptions import InsufficientStockError
from services.models import ServiceOrder
from services.services import ServiceOrderService
from stock.services import StockService


@pytest.fixture
def service_category(db):
    return Category.objects.create(name='Mão de Obra Oficina', type=Category.Type.SERVICE)


@pytest.fixture
def labor_product(db, service_category):
    return Product.objects.create(
        name='Sangria de Freio Hidráulico',
        sku='SERV-SANG-01',
        category=service_category,
        cost=Decimal('5.00'),
        price=Decimal('80.00'),
        is_service=True,
    )


@pytest.fixture
def part_product(db, category):
    return Product.objects.create(
        name='Óleo Mineral Shimano 100ml',
        sku='OLEO-SHIM-100',
        category=category,
        cost=Decimal('15.00'),
        price=Decimal('35.00'),
        is_service=False,
    )


@pytest.mark.django_db
class TestServiceOrderService:
    def test_create_order_happy_path(self, customer, warehouse):
        order = ServiceOrderService.create_order(
            customer=customer,
            warehouse=warehouse,
            bike_description='Specialized Chisel 29',
            client_reported_defect='Revisão geral e troca de óleo do freio',
            bike_serial_number='WSBC604123456N',
            accessories_left='Ciclocomputador Garmin',
        )
        assert order.status == ServiceOrder.Status.DRAFT
        assert order.customer == customer
        assert order.bike_serial_number == 'WSBC604123456N'

    def test_add_and_remove_items(self, customer, warehouse, labor_product, part_product):
        order = ServiceOrderService.create_order(
            customer=customer,
            warehouse=warehouse,
            bike_description='Caloi Elite',
            client_reported_defect='Revisão de freios',
        )

        ServiceOrderService.add_item(order, labor_product, quantity=1)
        item2 = ServiceOrderService.add_item(order, part_product, quantity=2)

        order.refresh_from_db()
        assert order.items.count() == 2
        # 1x 80 (servico) + 2x 35 (peca) = 150
        assert order.total_services == Decimal('80.00')
        assert order.total_parts == Decimal('70.00')
        assert order.total_amount == Decimal('150.00')

        # Remover item de peca
        ServiceOrderService.remove_item(order, item2.id)
        order.refresh_from_db()
        assert order.items.count() == 1
        assert order.total_parts == Decimal('0.00')
        assert order.total_amount == Decimal('80.00')

    def test_add_item_invalid_quantity_raises_value_error(self, customer, warehouse, labor_product):
        order = ServiceOrderService.create_order(
            customer=customer,
            warehouse=warehouse,
            bike_description='Caloi Elite',
            client_reported_defect='Barulho',
        )
        with pytest.raises(ValueError) as exc:
            ServiceOrderService.add_item(order, labor_product, quantity=0)
        assert 'maior que zero' in str(exc.value)

    def test_complete_order_deducts_stock_for_physical_parts_only(
        self, customer, warehouse, labor_product, part_product
    ):
        # 1. Abastecer estoque de pecas (5 unidades)
        StockService.add_stock(part_product, warehouse, 5)
        assert StockService.get_balance(part_product, warehouse) == 5

        # 2. Criar e preparar OS
        order = ServiceOrderService.create_order(
            customer=customer,
            warehouse=warehouse,
            bike_description='Scott Scale 960',
            client_reported_defect='Freio falhando',
        )
        ServiceOrderService.add_item(order, labor_product, quantity=1)
        ServiceOrderService.add_item(order, part_product, quantity=2)

        # 3. Ciclo de aprovacao e manutencao
        ServiceOrderService.approve_order(order)
        ServiceOrderService.start_maintenance(order)

        # 4. Conclusao da OS (dispara baixa de estoque das 2 pecas)
        ServiceOrderService.complete_order(order)
        order.refresh_from_db()
        assert order.status == ServiceOrder.Status.COMPLETED

        # Saldo de pecas deve cair de 5 para 3
        assert StockService.get_balance(part_product, warehouse) == 3
        # Saldo de servico imaterial continua 0 (nao existe saldo)
        assert StockService.get_balance(labor_product, warehouse) == 0

        # 5. Entrega da bike
        ServiceOrderService.deliver_order(order)
        order.refresh_from_db()
        assert order.status == ServiceOrder.Status.DELIVERED

    def test_complete_order_insufficient_stock_raises_error(
        self, customer, warehouse, part_product
    ):
        # Apenas 1 em estoque
        StockService.add_stock(part_product, warehouse, 1)

        order = ServiceOrderService.create_order(
            customer=customer,
            warehouse=warehouse,
            bike_description='Scott Scale',
            client_reported_defect='Troca de peca',
        )
        ServiceOrderService.add_item(order, part_product, quantity=3)  # Requer 3

        ServiceOrderService.approve_order(order)
        ServiceOrderService.start_maintenance(order)

        with pytest.raises(InsufficientStockError):
            ServiceOrderService.complete_order(order)

        # OS nao deve ter mudado para COMPLETED
        order.refresh_from_db()
        assert order.status == ServiceOrder.Status.IN_PROGRESS
        # Estoque permanece 1
        assert StockService.get_balance(part_product, warehouse) == 1

    def test_cancel_order_after_completed_restores_stock(self, customer, warehouse, part_product):
        StockService.add_stock(part_product, warehouse, 10)

        order = ServiceOrderService.create_order(
            customer=customer,
            warehouse=warehouse,
            bike_description='Cannondale Trail 5',
            client_reported_defect='Revisão',
        )
        ServiceOrderService.add_item(order, part_product, quantity=4)

        ServiceOrderService.approve_order(order)
        ServiceOrderService.start_maintenance(order)
        ServiceOrderService.complete_order(order)

        # Estoque caiu para 6
        assert StockService.get_balance(part_product, warehouse) == 6

        # Cancelamento estorna as 4 unidades
        ServiceOrderService.cancel_order(order)
        order.refresh_from_db()
        assert order.status == ServiceOrder.Status.CANCELLED
        assert StockService.get_balance(part_product, warehouse) == 10
