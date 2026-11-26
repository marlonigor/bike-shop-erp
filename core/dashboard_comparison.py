"""Compara vendas concluídas sem misturar depósitos ou sobrepor intervalos.

Exemplo: build_period_comparison(inicio, fim, deposito_id, total_atual, quantidade_atual).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from django.db.models import Count, Sum

from sales.models import Sale


@dataclass(frozen=True)
class ComparisonPeriod:
    """Intervalo inclusivo de referência; exemplo: 02/10 a 31/10."""

    start_date: date
    end_date: date


@dataclass(frozen=True)
class ComparisonMetric:
    """Valores comparáveis e tendência textual; exemplo: faturamento com alta de 20%."""

    label: str
    current: Decimal
    previous: Decimal
    monetary: bool
    percentage: Decimal | None
    trend: str


@dataclass(frozen=True)
class PeriodComparison:
    """Três indicadores com a mesma referência; exemplo: receita, vendas e ticket."""

    period: ComparisonPeriod | None
    metrics: tuple[ComparisonMetric, ...]
    has_previous_sales: bool


@dataclass(frozen=True)
class _SalesSnapshot:
    total: Decimal
    count: int

    @property
    def average(self) -> Decimal:
        return self.total / self.count if self.count else Decimal('0.00')


def previous_period(start_date: date, end_date: date) -> ComparisonPeriod | None:
    """Deriva o intervalo anterior completo; exemplo: 01/11–30/11 usa 02/10–31/10."""
    if start_date > end_date:
        raise ValueError(
            f'Intervalo recebido: {start_date} a {end_date}; esperado início até o fim.'
        )
    duration = (end_date - start_date).days + 1
    if start_date.toordinal() <= duration:
        return None
    return ComparisonPeriod(start_date - timedelta(days=duration), start_date - timedelta(days=1))


def _previous_sales(period: ComparisonPeriod | None, warehouse_id: UUID | None) -> _SalesSnapshot:
    if period is None:
        return _SalesSnapshot(Decimal('0.00'), 0)
    sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__date__range=(period.start_date, period.end_date),
    )
    if warehouse_id is not None:
        sales = sales.filter(warehouse_id=warehouse_id)
    totals = sales.aggregate(total=Sum('total_amount'), count=Count('pk'))
    return _SalesSnapshot(totals['total'] or Decimal('0.00'), totals['count'])


def _metric(label: str, current: Decimal, previous: Decimal, monetary: bool) -> ComparisonMetric:
    if previous == 0:
        return ComparisonMetric(label, current, previous, monetary, None, 'unavailable')
    percentage = (abs(current - previous) / previous * 100).quantize(Decimal('0.1'))
    trend = 'flat' if current == previous else 'up' if current > previous else 'down'
    return ComparisonMetric(label, current, previous, monetary, percentage, trend)


def _metrics(current: _SalesSnapshot, previous: _SalesSnapshot) -> tuple[ComparisonMetric, ...]:
    return (
        _metric('Faturamento', current.total, previous.total, True),
        _metric('Quantidade de vendas', Decimal(current.count), Decimal(previous.count), False),
        _metric('Ticket médio', current.average, previous.average, True),
    )


def build_period_comparison(
    start_date: date,
    end_date: date,
    warehouse_id: UUID | None,
    current_total: Decimal,
    current_count: int,
) -> PeriodComparison:
    """Reaproveita os totais atuais; exemplo: comparar 30 dias no mesmo depósito."""
    period = previous_period(start_date, end_date)
    previous = _previous_sales(period, warehouse_id)
    current = _SalesSnapshot(current_total, current_count)
    return PeriodComparison(period, _metrics(current, previous), previous.count > 0)
