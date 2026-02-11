import pytest
from django.urls import reverse
from catalog.models import Product, Category, Brand

@pytest.mark.django_db
class TestProductViews:
    
    @pytest.fixture
    def setup_data(self):
        category = Category.objects.create(name='Bikes', type='product')
        brand = Brand.objects.create(name='Caloi')
        product = Product.objects.create(
            name='Caloi 10',
            sku='CAL-001',
            price=1000.00,
            cost=500.00,
            category=category,
            brand=brand
        )
        return {'category': category, 'brand': brand, 'product': product}

    def test_product_list_view_returns_200(self, client, setup_data):
        url = reverse('catalog:product_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'products' in response.context
        assert setup_data['product'] in response.context['products']
        # Verifica se usa template v2
        assert 'catalog/product_list_v2.html' in [t.name for t in response.templates]

    def test_product_create_view_post_valid_data(self, client, setup_data):
        url = reverse('catalog:product_create')
        data = {
            'name': 'Nova Bike',
            'sku': 'NEW-001',
            'price': 1500.00,
            'cost': 800.00,
            'category': setup_data['category'].id,
            'brand': setup_data['brand'].id,
            'active': True
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Product.objects.filter(sku='NEW-001').exists()

    def test_product_create_view_validates_sku_unique(self, client, setup_data):
        url = reverse('catalog:product_create')
        data = {
            'name': 'Bike Duplicada',
            'sku': 'CAL-001', # Já existe
            'price': 1500.00,
            'cost': 800.00,
            'category': setup_data['category'].id,
            'brand': setup_data['brand'].id
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
            'active': True
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
        assert product.active is False # Soft delete
