"""Casos de fronteira da comparação automática de vendas."""

from datetime import date, datetime, time
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from core.dashboard_comparison import build_period_comparison, previous_period
from customers.models import Customer
from sales.models import Sale
from stock.models import Warehouse


@pytest.mark.parametrize(
    ('start', 'end', 'expected_start', 'expected_end'),
    [
        (date(2026, 11, 1), date(2026, 11, 30), date(2026, 10, 2), date(2026, 10, 31)),
        (date(2026, 1, 1), date(2026, 1, 1), date(2025, 12, 31), date(2025, 12, 31)),
        (date(2024, 3, 1), date(2024, 3, 1), date(2024, 2, 29), date(2024, 2, 29)),
    ],
)
def test_previous_period_has_equal_inclusive_duration(
    start: date, end: date, expected_start: date, expected_end: date
) -> None:
    """Não sobrepõe os intervalos mesmo ao atravessar meses e anos."""
    period = previous_period(start, end)

    assert period is not None
    assert (period.start_date, period.end_date) == (expected_start, expected_end)
    assert period.end_date < start
    assert period.end_date - period.start_date == end - start


def test_previous_period_handles_the_minimum_supported_date() -> None:
    """Evita estouro ao receber datas válidas sem um intervalo anterior possível."""
    assert previous_period(date.min, date(1, 1, 2)) is None


def test_previous_period_rejects_an_inverted_interval() -> None:
    """A fronteira pública exige datas ordenadas antes de calcular a referência."""
    with pytest.raises(ValueError, match='esperado início até o fim'):
        previous_period(date(2026, 11, 2), date(2026, 11, 1))


def _sale_on(
    customer: Customer, warehouse: Warehouse, day: date, amount: str, status: str = 'COMPLETED'
) -> Sale:
    sale = Sale.objects.create(
        customer=customer, warehouse=warehouse, total_amount=Decimal(amount), status=status
    )
    instant = timezone.make_aware(datetime.combine(day, time(12)))
    Sale.objects.filter(pk=sale.pk).update(created_at=instant)
    return sale


def _seed_period_sales(
    customer: Customer, warehouse: Warehouse, warehouse_secondary: Warehouse
) -> None:
    _sale_on(customer, warehouse, date(2026, 10, 2), '80.00')
    _sale_on(customer, warehouse, date(2026, 10, 31), '120.00')
    _sale_on(customer, warehouse, date(2026, 10, 1), '900.00')
    _sale_on(customer, warehouse_secondary, date(2026, 10, 15), '900.00')
    _sale_on(customer, warehouse, date(2026, 10, 15), '900.00', Sale.Status.CANCELLED)
    _sale_on(customer, warehouse, date(2026, 11, 1), '300.00')


@pytest.mark.django_db
def test_comparison_uses_completed_sales_and_the_same_warehouse(
    client: Client, customer: Customer, warehouse: Warehouse, warehouse_secondary: Warehouse
) -> None:
    """Isola depósito, status e limites inclusivos do período de referência."""
    _seed_period_sales(customer, warehouse, warehouse_secondary)
    response = client.get(
        reverse('dashboard'),
        {
            'start_date': '2026-11-01',
            'end_date': '2026-11-30',
            'warehouse': str(warehouse.id),
        },
    )
    metrics = response.context['period_comparison'].metrics

    assert [metric.previous for metric in metrics] == [Decimal('200.00'), 2, Decimal('100.00')]
    assert [metric.current for metric in metrics] == [Decimal('300.00'), 1, Decimal('300.00')]
    assert [metric.percentage for metric in metrics] == [50, 50, 200]
    assert [metric.trend for metric in metrics] == ['up', 'down', 'up']


@pytest.mark.django_db
def test_comparison_does_not_invent_a_percentage_without_a_baseline(client: Client) -> None:
    """Explica a ausência de base sem divisão por zero ou crescimento fictício."""
    response = client.get(reverse('dashboard'))
    comparison = response.context['period_comparison']

    assert comparison.has_previous_sales is False
    assert all(metric.percentage is None for metric in comparison.metrics)
    assert 'Sem base anterior para calcular a variação' in response.content.decode()


@pytest.mark.django_db
def test_comparison_handles_a_drop_to_zero(customer: Customer, warehouse: Warehouse) -> None:
    """Uma queda de vendas para zero corresponde a redução real de 100%."""
    _sale_on(customer, warehouse, date(2026, 10, 31), '100.00')
    comparison = build_period_comparison(
        date(2026, 11, 1), date(2026, 11, 1), warehouse.id, Decimal('0.00'), 0
    )

    assert all(metric.percentage == 100 for metric in comparison.metrics)
    assert all(metric.trend == 'down' for metric in comparison.metrics)


@pytest.mark.django_db
def test_comparison_marks_equal_sales_as_unchanged(
    customer: Customer, warehouse: Warehouse
) -> None:
    """Evita sinalizar crescimento quando os valores são idênticos."""
    _sale_on(customer, warehouse, date(2026, 10, 31), '100.00')
    comparison = build_period_comparison(
        date(2026, 11, 1), date(2026, 11, 1), warehouse.id, Decimal('100.00'), 1
    )

    assert all(metric.percentage == 0 for metric in comparison.metrics)
    assert all(metric.trend == 'flat' for metric in comparison.metrics)


@pytest.mark.django_db
def test_comparison_has_no_percentage_for_new_sales_without_previous_sales(
    customer: Customer, warehouse: Warehouse
) -> None:
    """A primeira venda não representa crescimento calculável de 100%."""
    comparison = build_period_comparison(
        date(2026, 11, 1), date(2026, 11, 1), warehouse.id, Decimal('100.00'), 1
    )

    assert comparison.has_previous_sales is False
    assert [metric.current for metric in comparison.metrics] == [100, 1, 100]
    assert all(metric.percentage is None for metric in comparison.metrics)


@pytest.mark.django_db
def test_comparison_consolidates_warehouses_and_rounds_percentage(
    customer: Customer, warehouse: Warehouse, warehouse_secondary: Warehouse
) -> None:
    """Todos os depósitos usa a mesma consolidação, mantendo precisão decimal."""
    _sale_on(customer, warehouse, date(2026, 10, 31), '100.00')
    _sale_on(customer, warehouse_secondary, date(2026, 10, 31), '200.00')
    comparison = build_period_comparison(
        date(2026, 11, 1), date(2026, 11, 1), None, Decimal('400.00'), 2
    )

    assert comparison.metrics[0].previous == Decimal('300.00')
    assert comparison.metrics[0].percentage == Decimal('33.3')
    assert comparison.metrics[1].trend == 'flat'


@pytest.mark.django_db
def test_comparison_handles_an_unavailable_reference_period() -> None:
    """Preserva os valores atuais quando não há datas anteriores representáveis."""
    comparison = build_period_comparison(date.min, date(1, 1, 2), None, Decimal('0.00'), 0)

    assert comparison.period is None
    assert comparison.has_previous_sales is False


@pytest.mark.django_db
def test_small_percentage_changes_do_not_display_as_unchanged(
    client: Client, customer: Customer, warehouse: Warehouse
) -> None:
    """Diferencia uma variação inferior à precisão visual de um empate real."""
    _sale_on(customer, warehouse, date(2026, 10, 31), '10000.00')
    _sale_on(customer, warehouse, date(2026, 11, 1), '10001.00')
    response = client.get(
        reverse('dashboard'), {'start_date': '2026-11-01', 'end_date': '2026-11-01'}
    )

    assert 'Aumento inferior a 0,1%.' in response.content.decode()
