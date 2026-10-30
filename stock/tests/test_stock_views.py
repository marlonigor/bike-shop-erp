"""Testes unitários e de integração para controladores de estoque."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from catalog.models import Category, Product
from stock.models import StockMovement, Warehouse


@pytest.mark.django_db
class TestStockHistoryView:
    @pytest.fixture
    def setup_data(self):
        category = Category.objects.create(name='Peças')
        warehouse = Warehouse.objects.create(name='Principal', location='Galpão 1')
        product_a = Product.objects.create(
            name='Câmara de Ar', sku='CAM-001', price=30.0, cost=15.0, category=category
        )
        product_b = Product.objects.create(
            name='Pneu 29', sku='PNEU-001', price=100.0, cost=50.0, category=category
        )
        return {
            'warehouse': warehouse,
            'product_a': product_a,
            'product_b': product_b,
        }

    def test_stock_history_returns_200(self, client, setup_data):
        url = reverse('stock:stock_history')
        response = client.get(url)
        assert response.status_code == 200
        assert 'stock/stock_history.html' in [t.name for t in response.templates]
        assert 'page_obj' in response.context
        assert 'products' in response.context

    def test_stock_history_htmx_returns_partial(self, client, setup_data):
        url = reverse('stock:stock_history')
        response = client.get(url, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert 'stock/partials/history_table.html' in [t.name for t in response.templates]

    def test_stock_history_filter_by_product_and_type(self, client, setup_data):
        warehouse = setup_data['warehouse']
        prod_a = setup_data['product_a']
        prod_b = setup_data['product_b']

        StockMovement.objects.create(
            product=prod_a,
            warehouse=warehouse,
            quantity=5,
            movement_type=StockMovement.MovementType.IN,
        )
        StockMovement.objects.create(
            product=prod_b,
            warehouse=warehouse,
            quantity=2,
            movement_type=StockMovement.MovementType.IN,
        )

        url = reverse('stock:stock_history')
        response_a = client.get(f'{url}?product={prod_a.id}')
        assert len(response_a.context['movements']) == 1
        assert response_a.context['movements'][0].product == prod_a

        response_in = client.get(f'{url}?type=IN')
        assert len(response_in.context['movements']) == 2
        assert response_in.context['movements'][0].movement_type == 'IN'

    def test_stock_history_filter_by_period(self, client, setup_data):
        warehouse = setup_data['warehouse']
        prod = setup_data['product_a']
        now = timezone.now()

        mov_old = StockMovement.objects.create(
            product=prod, warehouse=warehouse, quantity=10, movement_type='IN'
        )
        StockMovement.objects.filter(pk=mov_old.pk).update(created_at=now - timedelta(days=10))

        mov_recent = StockMovement.objects.create(
            product=prod, warehouse=warehouse, quantity=5, movement_type='IN'
        )

        url = reverse('stock:stock_history')
        start_date = (now - timedelta(days=2)).strftime('%Y-%m-%d')
        response = client.get(f'{url}?start_date={start_date}')
        movements = list(response.context['movements'])
        assert len(movements) == 1
        assert movements[0].pk == mov_recent.pk

    def test_stock_history_pagination(self, client, setup_data):
        warehouse = setup_data['warehouse']
        prod = setup_data['product_a']

        movements = [
            StockMovement(product=prod, warehouse=warehouse, quantity=i + 1, movement_type='IN')
            for i in range(25)
        ]
        StockMovement.objects.bulk_create(movements)

        url = reverse('stock:stock_history')
        response_page1 = client.get(url)
        assert len(response_page1.context['movements']) == 20
        assert response_page1.context['page_obj'].has_next()

        response_page2 = client.get(f'{url}?page=2')
        assert len(response_page2.context['movements']) == 5
        assert response_page2.context['page_obj'].has_previous()
