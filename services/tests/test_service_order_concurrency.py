"""
Testes de resiliencia, controle de concorrencia e integridade transacional.
Valida comportamento atomico, bloqueio pessimista e prevencao de race conditions no ciclo da OS.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connection

from catalog.models import Category, Product
from core.exceptions import InsufficientStockError, InvalidStatusTransitionError
from services.models import ServiceOrder, ServiceOrderItem
from services.services import ServiceOrderService
from stock.models import Stock, StockMovement
from stock.services import StockService


@pytest.fixture
def physical_product(db):
    cat = Category.objects.create(name='Pecas Fisicas', type=Category.Type.PRODUCT)
    return Product.objects.create(
        name='Corrente Shimano Deore 12v',
        sku='SHIM-CORR-12V',
        category=cat,
        cost=Decimal('80.00'),
        price=Decimal('150.00'),
        is_service=False,
    )


@pytest.fixture
def in_progress_order(db, customer, warehouse):
    return ServiceOrder.objects.create(
        customer=customer,
        warehouse=warehouse,
        bike_description='Specialized Epic Expert',
        client_reported_defect='Troca de transmissao',
        status=ServiceOrder.Status.IN_PROGRESS,
    )


def _setup_concurrency_order(customer, warehouse, product) -> ServiceOrder:
    """Prepara a ordem e estoque para teste de concorrencia."""
    StockService.add_stock(
        product=product,
        warehouse=warehouse,
        quantity=10,
        reference_type=StockMovement.ReferenceType.MANUAL,
        reason='Estoque inicial de seguranca',
    )
    order = ServiceOrder.objects.create(
        customer=customer,
        warehouse=warehouse,
        bike_description='Scott Spark RC',
        client_reported_defect='Instalacao de corrente',
        status=ServiceOrder.Status.IN_PROGRESS,
    )
    ServiceOrderItem.objects.create(
        service_order=order,
        product=product,
        quantity=2,
        unit_price=Decimal('150.00'),
        total_price=Decimal('300.00'),
    )
    return order


def _run_concurrent_completion(order: ServiceOrder) -> tuple[int, int]:
    """Dispara execucao concorrente do complete_order em 2 threads."""

    def _execute() -> bool:
        try:
            ServiceOrderService.complete_order(order)
            return True
        except InvalidStatusTransitionError:
            return False
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: _execute(), range(2)))
    return sum(1 for r in results if r), sum(1 for r in results if not r)


@pytest.mark.django_db(transaction=True)
class TestServiceOrderConcurrencyAndResilience:
    def test_concurrent_complete_order_executes_only_once(
        self, customer, warehouse, physical_product
    ):
        """Dois processos concorrentes tentando concluir a mesma OS devem ser serializados."""
        order = _setup_concurrency_order(customer, warehouse, physical_product)
        successes, errors = _run_concurrent_completion(order)

        assert (successes, errors) == (1, 1)
        order.refresh_from_db()
        assert order.status == ServiceOrder.Status.COMPLETED

        stock_record = Stock.objects.get(product=physical_product, warehouse=warehouse)
        assert stock_record.quantity == 8

    def test_atomic_rollback_on_insufficient_stock_during_completion(
        self, in_progress_order, physical_product, warehouse
    ):
        """Se um dos itens nao possuir saldo suficiente, toda a transicao deve ser revertida."""
        StockService.add_stock(
            product=physical_product, warehouse=warehouse, quantity=1, reason='Saldo'
        )
        ServiceOrderItem.objects.create(
            service_order=in_progress_order,
            product=physical_product,
            quantity=5,
            unit_price=Decimal('150.00'),
            total_price=Decimal('750.00'),
        )
        with pytest.raises(InsufficientStockError):
            ServiceOrderService.complete_order(in_progress_order)

        in_progress_order.refresh_from_db()
        assert in_progress_order.status == ServiceOrder.Status.IN_PROGRESS
        stock_record = Stock.objects.get(product=physical_product, warehouse=warehouse)
        assert stock_record.quantity == 1

    def test_cannot_add_item_to_finalized_order(self, in_progress_order, physical_product):
        """Valida que ordens concluidas ou canceladas rejeitam insercao de novos itens."""
        in_progress_order.status = ServiceOrder.Status.COMPLETED
        in_progress_order.save()

        with pytest.raises(ValueError, match='Operacao negada'):
            ServiceOrderService.add_item(
                order=in_progress_order,
                product=physical_product,
                quantity=1,
            )

    def test_cannot_remove_item_from_finalized_order(self, in_progress_order, physical_product):
        """Valida que ordens concluidas ou canceladas rejeitam exclusao de itens."""
        item = ServiceOrderItem.objects.create(
            service_order=in_progress_order,
            product=physical_product,
            quantity=1,
            unit_price=Decimal('150.00'),
            total_price=Decimal('150.00'),
        )
        in_progress_order.status = ServiceOrder.Status.CANCELLED
        in_progress_order.save()

        with pytest.raises(ValueError, match='Operacao negada'):
            ServiceOrderService.remove_item(order=in_progress_order, item_id=item.id)
