from decimal import Decimal

import pytest

from catalog.models import Category, Product
from core.exceptions import InvalidStatusTransitionError
from services.models import ServiceOrder, ServiceOrderItem


@pytest.fixture
def service_category(db):
    return Category.objects.create(name='Mão de Obra', type=Category.Type.SERVICE)


@pytest.fixture
def labor_product(db, service_category):
    return Product.objects.create(
        name='Revisão Básica',
        sku='REV-BASICA',
        category=service_category,
        cost=Decimal('0.00'),
        price=Decimal('120.00'),
        is_service=True,
    )


@pytest.fixture
def part_product(db, category):
    return Product.objects.create(
        name='Pastilha de Freio Shimano',
        sku='PAST-SHIM-01',
        category=category,
        cost=Decimal('20.00'),
        price=Decimal('45.00'),
        is_service=False,
    )


@pytest.fixture
def service_order(db, customer, warehouse):
    return ServiceOrder.objects.create(
        customer=customer,
        warehouse=warehouse,
        bike_description='Trek Marlin 7 Azul',
        client_reported_defect='Freio traseiro borrachudo e marchas pulando',
    )


@pytest.mark.django_db
class TestServiceOrderModels:
    def test_service_order_initial_state(self, service_order):
        assert service_order.status == ServiceOrder.Status.DRAFT
        assert service_order.total_amount == Decimal('0.00')
        assert service_order.total_parts == Decimal('0.00')
        assert service_order.total_services == Decimal('0.00')
        assert 'Trek Marlin 7' in str(service_order)

    def test_service_order_item_calculates_total_price(self, service_order, labor_product):
        item = ServiceOrderItem.objects.create(
            service_order=service_order,
            product=labor_product,
            quantity=2,
            unit_price=Decimal('120.00'),
        )
        assert item.total_price == Decimal('240.00')
        assert item.is_service is True

    def test_recalculate_totals_separates_parts_and_services(
        self, service_order, labor_product, part_product
    ):
        # 1 servico de 120 e 2 pecas de 45 (total 90) -> Total bruto 210, desconto 10 = 200
        ServiceOrderItem.objects.create(
            service_order=service_order,
            product=labor_product,
            quantity=1,
            unit_price=Decimal('120.00'),
        )
        ServiceOrderItem.objects.create(
            service_order=service_order,
            product=part_product,
            quantity=2,
            unit_price=Decimal('45.00'),
        )
        service_order.discount = Decimal('10.00')
        service_order.recalculate_totals()

        service_order.refresh_from_db()
        assert service_order.total_services == Decimal('120.00')
        assert service_order.total_parts == Decimal('90.00')
        assert service_order.total_amount == Decimal('200.00')

    def test_valid_status_transitions(self, service_order):
        assert service_order.can_transition_to(ServiceOrder.Status.APPROVED) is True
        assert service_order.can_transition_to(ServiceOrder.Status.CANCELLED) is True
        assert service_order.can_transition_to(ServiceOrder.Status.DELIVERED) is False

        service_order.change_status(ServiceOrder.Status.APPROVED)
        assert service_order.status == ServiceOrder.Status.APPROVED

        service_order.change_status(ServiceOrder.Status.IN_PROGRESS)
        assert service_order.status == ServiceOrder.Status.IN_PROGRESS

        service_order.change_status(ServiceOrder.Status.COMPLETED)
        assert service_order.status == ServiceOrder.Status.COMPLETED
        assert service_order.completed_at is not None

        service_order.change_status(ServiceOrder.Status.DELIVERED)
        assert service_order.status == ServiceOrder.Status.DELIVERED
        assert service_order.delivered_at is not None

    def test_invalid_status_transition_raises_error(self, service_order):
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            service_order.change_status(ServiceOrder.Status.DELIVERED)

        assert 'ServiceOrder' in str(exc_info.value)
        assert 'DRAFT' in str(exc_info.value)
        assert 'DELIVERED' in str(exc_info.value)
