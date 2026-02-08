import pytest
from django.urls import reverse
from catalog.models import Brand

@pytest.mark.django_db
class TestBrandViews:
    
    def test_brand_list_view_returns_200(self, client):
        url = reverse('catalog:brand_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'brands' in response.context
        assert 'catalog/brand_list.html' in [t.name for t in response.templates]

    def test_brand_create_view_post_valid_data(self, client):
        url = reverse('catalog:brand_create')
        data = {
            'name': 'Nova Marca'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Brand.objects.filter(name='Nova Marca').exists()

    def test_brand_edit_view_updates_data(self, client):
        brand = Brand.objects.create(name='Marca Antiga')
        url = reverse('catalog:brand_edit', args=[brand.id])
        data = {
            'name': 'Marca Editada'
        }
        response = client.post(url, data)
        assert response.status_code == 302
        
        brand.refresh_from_db()
        assert brand.name == 'Marca Editada'

    def test_brand_delete_view_removes_data(self, client):
        brand = Brand.objects.create(name='Marca Para Deletar')
        url = reverse('catalog:brand_delete', args=[brand.id])
        
        response = client.post(url)
        assert response.status_code == 302
        assert not Brand.objects.filter(id=brand.id).exists()
