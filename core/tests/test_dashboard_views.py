from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from sales.models import Sale, SaleItem
from services.models import ServiceOrder
from stock.models import Stock, Warehouse


@pytest.mark.django_db
class TestDashboardView:
    def test_dashboard_returns_200(self, client):
        url = reverse('dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert 'core/dashboard.html' in [t.name for t in response.templates]
        assert 'total_vendas' in response.context
        assert 'vendas_no_periodo' in response.context
        assert 'ordens_ativas' in response.context
        assert 'produtos_baixo_estoque' in response.context
        assert 'service_order_statuses' in response.context
        assert 'top_products' in response.context
        assert b'name="start_date"' in response.content
        assert b'OS Abertas no Per' in response.content

    def test_dashboard_uses_the_default_thirty_day_period(self, client, customer, warehouse):
        now = timezone.now()

        # Venda realizada hoje
        Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=Decimal('100.00'),
            status=Sale.Status.COMPLETED,
        )

        # Venda realizada no passado
        sale_past = Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=Decimal('200.00'),
            status=Sale.Status.COMPLETED,
        )
        Sale.objects.filter(pk=sale_past.pk).update(created_at=now - timedelta(days=31))

        url = reverse('dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['vendas_no_periodo'] == 1
        assert response.context['total_vendas'] == Decimal('100.00')

    def test_dashboard_filters_by_selected_period(self, client, customer, warehouse) -> None:
        today = timezone.localdate()
        recent_sale = Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=Decimal('120.00'),
            status=Sale.Status.COMPLETED,
        )
        Sale.objects.filter(pk=recent_sale.pk).update(created_at=timezone.now() - timedelta(days=1))
        Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=Decimal('80.00'),
            status=Sale.Status.COMPLETED,
        )

        response = client.get(
            reverse('dashboard'), {'start_date': today.isoformat(), 'end_date': today.isoformat()}
        )

        assert response.context['total_vendas'] == Decimal('80.00')
        assert response.context['vendas_no_periodo'] == 1

    def test_dashboard_normalizes_an_inverted_period(self, client, customer, warehouse) -> None:
        today = timezone.localdate()
        Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=Decimal('80.00'),
            status=Sale.Status.COMPLETED,
        )

        response = client.get(
            reverse('dashboard'),
            {'start_date': today.isoformat(), 'end_date': (today - timedelta(days=1)).isoformat()},
        )

        assert response.context['filters'].start_date == today - timedelta(days=1)
        assert response.context['filters'].end_date == today
        assert response.context['vendas_no_periodo'] == 1

    def test_dashboard_ignores_an_invalid_warehouse_identifier(self, client) -> None:
        response = client.get(reverse('dashboard'), {'warehouse': 'invalid-warehouse'})

        assert response.status_code == 200
        assert response.context['selected_warehouse'] == ''

    def test_dashboard_baixo_estoque_alerts(self, client, product, warehouse):
        Stock.objects.create(product=product, warehouse=warehouse, quantity=3)

        url = reverse('dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['produtos_baixo_estoque'] == 1
        assert len(response.context['alertas_estoque']) == 1

    def test_dashboard_filters_sales_orders_and_stock_by_warehouse(
        self, client, customer, warehouse, product
    ) -> None:
        other_warehouse = Warehouse.objects.create(name='Oficina', location='Fundos')
        Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=Decimal('100.00'),
            status=Sale.Status.COMPLETED,
        )
        Sale.objects.create(
            customer=customer,
            warehouse=other_warehouse,
            total_amount=Decimal('200.00'),
            status=Sale.Status.COMPLETED,
        )
        ServiceOrder.objects.create(
            customer=customer,
            warehouse=warehouse,
            bike_description='Bike da loja',
            client_reported_defect='Revisão',
            status=ServiceOrder.Status.IN_PROGRESS,
        )
        ServiceOrder.objects.create(
            customer=customer,
            warehouse=other_warehouse,
            bike_description='Bike da oficina',
            client_reported_defect='Freio',
            status=ServiceOrder.Status.APPROVED,
        )
        Stock.objects.create(product=product, warehouse=warehouse, quantity=3)
        Stock.objects.create(product=product, warehouse=other_warehouse, quantity=2)

        response = client.get(reverse('dashboard'), {'warehouse': str(warehouse.id)})

        statuses = {item.status: item.count for item in response.context['service_order_statuses']}
        assert response.context['total_vendas'] == Decimal('100.00')
        assert response.context['ordens_ativas'] == 1
        assert response.context['produtos_baixo_estoque'] == 1
        assert statuses[ServiceOrder.Status.IN_PROGRESS] == 1
        assert statuses[ServiceOrder.Status.APPROVED] == 0
        assert f'warehouse={warehouse.id}'.encode() in response.content

    def test_dashboard_lists_top_products_in_the_selected_period(
        self, client, customer, warehouse, product
    ) -> None:
        sale = Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=Decimal('240.00'),
            status=Sale.Status.COMPLETED,
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=3,
            unit_price=Decimal('80.00'),
            total_price=Decimal('240.00'),
        )

        response = client.get(reverse('dashboard'))

        top_product = response.context['top_products'][0]
        assert top_product.name == product.name
        assert top_product.quantity == 3
        assert top_product.revenue == Decimal('240.00')

    def test_dashboard_skips_chart_initialization_when_no_sales(self, client: Client) -> None:
        """Impede erro no navegador quando o estado vazio omite o canvas."""
        response = client.get(reverse('dashboard'))

        assert b'id="salesChart"' not in response.content
        assert b'if (!chartElement)' in response.content
