from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from sales.models import Sale
from stock.models import Stock


@pytest.mark.django_db
class TestDashboardView:
    def test_dashboard_returns_200(self, client):
        url = reverse('dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert 'core/dashboard.html' in [t.name for t in response.templates]
        assert 'total_vendas' in response.context
        assert 'vendas_hoje' in response.context
        assert 'produtos_ativos' in response.context
        assert 'produtos_baixo_estoque' in response.context

    def test_dashboard_vendas_hoje_only_counts_today_sales(self, client, customer, warehouse):
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
        Sale.objects.filter(pk=sale_past.pk).update(created_at=now - timedelta(days=5))

        url = reverse('dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['vendas_hoje'] == 1
        assert response.context['total_vendas'] == Decimal('300.00')

    def test_dashboard_baixo_estoque_alerts(self, client, product, warehouse):
        Stock.objects.create(product=product, warehouse=warehouse, quantity=3)

        url = reverse('dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['produtos_baixo_estoque'] == 1
        assert len(response.context['alertas_estoque']) == 1
