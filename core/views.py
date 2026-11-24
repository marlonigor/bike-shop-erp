from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from django.db.models import QuerySet, Sum, functions
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from sales.models import Sale, SaleItem
from services.models import ServiceOrder
from stock.models import Stock, Warehouse

DEFAULT_DASHBOARD_DAYS = 30
LOW_STOCK_LIMIT = 5


@dataclass(frozen=True)
class DashboardFilters:
    """Representa o recorte de periodo e deposito escolhido no painel."""

    start_date: date
    end_date: date
    warehouse_id: UUID | None


@dataclass(frozen=True)
class ServiceOrderStatusMetric:
    """Agrupa a quantidade de OS de um status para exibicao no painel."""

    status: str
    label: str
    count: int


@dataclass(frozen=True)
class DashboardMetrics:
    """Concentra os quatro indicadores principais do recorte selecionado."""

    total_sales: Decimal
    sales_count: int
    active_orders: int
    low_stock_count: int


@dataclass(frozen=True)
class TopProductMetric:
    """Representa o desempenho de um produto vendido no período."""

    name: str
    sku: str
    quantity: int
    revenue: Decimal


@dataclass(frozen=True)
class DashboardData:
    """Agrupa as consultas calculadas antes da montagem do contexto da tela."""

    filters: DashboardFilters
    sales: QuerySet[Sale]
    orders: QuerySet[ServiceOrder]
    low_stock: QuerySet[Stock]
    metrics: DashboardMetrics
    chart_labels: list[str]
    chart_data: list[float]


class DashboardContext(TypedDict):
    """Descreve os dados disponibilizados ao template do painel gerencial."""

    filters: DashboardFilters
    warehouses: QuerySet[Warehouse]
    selected_warehouse: str
    total_vendas: Decimal
    vendas_no_periodo: int
    ordens_ativas: int
    produtos_baixo_estoque: int
    service_order_statuses: list[ServiceOrderStatusMetric]
    top_products: list[TopProductMetric]
    ultimas_vendas: QuerySet[Sale]
    alertas_estoque: QuerySet[Stock]
    chart_labels: list[str]
    chart_data: list[float]


def _default_date_range() -> tuple[date, date]:
    today = timezone.localdate()
    return today - timedelta(days=DEFAULT_DASHBOARD_DAYS - 1), today


def _parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def _parse_warehouse_id(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _dashboard_filters(request: HttpRequest) -> DashboardFilters:
    default_start, default_end = _default_date_range()
    start_date = _parse_date(request.GET.get('start_date'), default_start)
    end_date = _parse_date(request.GET.get('end_date'), default_end)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return DashboardFilters(start_date, end_date, _parse_warehouse_id(request.GET.get('warehouse')))


def _filtered_sales(filters: DashboardFilters) -> QuerySet[Sale]:
    sales = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__date__range=(filters.start_date, filters.end_date),
    )
    if filters.warehouse_id is not None:
        return sales.filter(warehouse_id=filters.warehouse_id)
    return sales


def _filtered_orders(filters: DashboardFilters) -> QuerySet[ServiceOrder]:
    orders = ServiceOrder.objects.filter(
        created_at__date__range=(filters.start_date, filters.end_date)
    )
    if filters.warehouse_id is not None:
        return orders.filter(warehouse_id=filters.warehouse_id)
    return orders


def _low_stock(filters: DashboardFilters) -> QuerySet[Stock]:
    stocks = Stock.objects.filter(quantity__lt=LOW_STOCK_LIMIT)
    if filters.warehouse_id is not None:
        return stocks.filter(warehouse_id=filters.warehouse_id)
    return stocks


def _status_metrics(orders: QuerySet[ServiceOrder]) -> list[ServiceOrderStatusMetric]:
    labels = dict(ServiceOrder.Status.choices)
    return [
        ServiceOrderStatusMetric(status, labels[status], orders.filter(status=status).count())
        for status in ServiceOrder.Status.values
    ]


def _dashboard_metrics(
    sales: QuerySet[Sale], orders: QuerySet[ServiceOrder], low_stock: QuerySet[Stock]
) -> DashboardMetrics:
    total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    active_orders = orders.exclude(
        status__in=[ServiceOrder.Status.DELIVERED, ServiceOrder.Status.CANCELLED]
    ).count()
    return DashboardMetrics(total_sales, sales.count(), active_orders, low_stock.count())


def _top_products(sales: QuerySet[Sale]) -> list[TopProductMetric]:
    product_rows = (
        SaleItem.objects.filter(sale__in=sales)
        .values('product__name', 'product__sku')
        .annotate(quantity=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-quantity', 'product__name')[:5]
    )
    return [
        TopProductMetric(row['product__name'], row['product__sku'], row['quantity'], row['revenue'])
        for row in product_rows
    ]


def _sales_chart(sales: QuerySet[Sale]) -> tuple[list[str], list[float]]:
    chart_data = sales.annotate(day=functions.TruncDate('created_at')).values('day')
    chart_data = chart_data.annotate(total=Sum('total_amount')).order_by('day')
    labels = [sale['day'].strftime('%d/%m') for sale in chart_data]
    return labels, [float(sale['total']) for sale in chart_data]


def _dashboard_data(filters: DashboardFilters) -> DashboardData:
    # Estatísticas
    sales = _filtered_sales(filters)
    orders = _filtered_orders(filters)
    low_stock = _low_stock(filters)
    metrics = _dashboard_metrics(sales, orders, low_stock)
    chart_labels, chart_data = _sales_chart(sales)
    return DashboardData(filters, sales, orders, low_stock, metrics, chart_labels, chart_data)


def _dashboard_recent_records(data: DashboardData) -> tuple[QuerySet[Sale], QuerySet[Stock]]:
    # Últimas vendas
    recent_sales = data.sales.select_related('customer').order_by('-created_at')[:5]
    # Alertas de estoque
    stock_alerts = data.low_stock.select_related('product', 'warehouse').order_by('quantity')[:5]
    return recent_sales, stock_alerts


def _dashboard_context(data: DashboardData) -> DashboardContext:
    recent_sales, stock_alerts = _dashboard_recent_records(data)
    # Dados para o gráfico diário do período
    return {
        'filters': data.filters,
        'warehouses': Warehouse.objects.order_by('name'),
        'selected_warehouse': str(data.filters.warehouse_id or ''),
        'total_vendas': data.metrics.total_sales,
        'vendas_no_periodo': data.metrics.sales_count,
        'ordens_ativas': data.metrics.active_orders,
        'produtos_baixo_estoque': data.metrics.low_stock_count,
        'service_order_statuses': _status_metrics(data.orders),
        'top_products': _top_products(data.sales),
        'ultimas_vendas': recent_sales,
        'alertas_estoque': stock_alerts,
        'chart_labels': data.chart_labels,
        'chart_data': data.chart_data,
    }


def dashboard(request: HttpRequest) -> HttpResponse:
    """Exibe indicadores de vendas, oficina e estoque para a gestao."""
    filters = _dashboard_filters(request)
    return render(request, 'core/dashboard.html', _dashboard_context(_dashboard_data(filters)))
