from decimal import Decimal

import pytest
from django.urls import reverse

from catalog.models import Brand, Category, Product


@pytest.mark.django_db
class TestProductViews:
    @pytest.fixture
    def setup_data(self):
        category = Category.objects.create(name='Bikes', type='product')
        brand = Brand.objects.create(name='Caloi')
        product = Product.objects.create(
            name='Caloi 10',
            sku='CAL-001',
            price=Decimal('1000.00'),
            cost=Decimal('500.00'),
            category=category,
            brand=brand,
        )
        return {'category': category, 'brand': brand, 'product': product}

    def test_product_list_view_returns_200(self, client, setup_data):
        url = reverse('catalog:product_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'products' in response.context
        assert setup_data['product'] in response.context['products']
        assert 'catalog/product_list.html' in [t.name for t in response.templates]

    def test_product_create_view_post_valid_data(self, client, setup_data):
        url = reverse('catalog:product_create')
        data = {
            'name': 'Nova Bike',
            'sku': 'NEW-001',
            'price': 1500.00,
            'cost': 800.00,
            'category': setup_data['category'].id,
            'brand': setup_data['brand'].id,
            'active': True,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Product.objects.filter(sku='NEW-001').exists()

    def test_product_create_view_validates_sku_unique(self, client, setup_data):
        url = reverse('catalog:product_create')
        data = {
            'name': 'Bike Duplicada',
            'sku': 'CAL-001',  # Já existe
            'price': 1500.00,
            'cost': 800.00,
            'category': setup_data['category'].id,
            'brand': setup_data['brand'].id,
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors['sku']

    def test_product_edit_view_updates_data(self, client, setup_data):
        product = setup_data['product']
        url = reverse('catalog:product_edit', args=[product.id])
        data = {
            'name': 'Caloi 10 Editada',
            'sku': product.sku,
            'price': 1200.00,
            'cost': 500.00,
            'category': setup_data['category'].id,
            'brand': setup_data['brand'].id,
            'active': True,
        }
        response = client.post(url, data)
        assert response.status_code == 302

        product.refresh_from_db()
        assert product.name == 'Caloi 10 Editada'
        assert product.price == 1200.00

    def test_product_delete_view_soft_delete(self, client, setup_data):
        product = setup_data['product']
        url = reverse('catalog:product_delete', args=[product.id])

        response = client.post(url)
        assert response.status_code == 302

        product.refresh_from_db()
        assert product.active is False  # Soft delete

    def test_product_detail_view_computes_aggregated_metrics_across_all_sales(
        self, client, setup_data, customer, warehouse
    ):
        from sales.models import Sale, SaleItem

        product = setup_data['product']

        # Criar 12 vendas com 2 unidades cada (total 24 un, R$ 24.000,00)
        for _ in range(12):
            sale = Sale.objects.create(
                customer=customer,
                warehouse=warehouse,
                total_amount=Decimal('2000.00'),
                status=Sale.Status.COMPLETED,
            )
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=2,
                unit_price=Decimal('1000.00'),
                total_price=Decimal('2000.00'),
            )

        url = reverse('catalog:product_detail', args=[product.id])
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.context['sales_history']) == 10
        assert response.context['total_sold'] == 24
        assert response.context['total_revenue'] == Decimal('24000.00')
