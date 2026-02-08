import pytest
from django.urls import reverse
from catalog.models import Category

@pytest.mark.django_db
class TestCategoryViews:
    
    def test_category_list_view_returns_200(self, client):
        url = reverse('catalog:category_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'categories' in response.context
        assert 'catalog/category_list.html' in [t.name for t in response.templates]

    def test_category_create_view_post_valid_data(self, client):
        url = reverse('catalog:category_create')
        data = {
            'name': 'Nova Categoria',
            'type': Category.Type.PRODUCT
        }
        response = client.post(url, data)
        assert response.status_code == 302 # Redirect
        assert Category.objects.filter(name='Nova Categoria').exists()

    def test_category_create_view_post_invalid_data(self, client):
        url = reverse('catalog:category_create')
        data = {
            'name': '', # Nome obrigatório
            'type': Category.Type.PRODUCT
        }
        response = client.post(url, data)
        assert response.status_code == 200 # Fica na página com erro
        assert not Category.objects.filter(name='').exists()
        assert 'form' in response.context
        assert response.context['form'].errors['name']

    def test_category_edit_view_updates_data(self, client):
        category = Category.objects.create(name='Categoria Antiga', type=Category.Type.PRODUCT)
        url = reverse('catalog:category_edit', args=[category.id])
        data = {
            'name': 'Categoria Editada',
            'type': Category.Type.SERVICE
        }
        response = client.post(url, data)
        assert response.status_code == 302
        
        category.refresh_from_db()
        assert category.name == 'Categoria Editada'
        assert category.type == Category.Type.SERVICE

    def test_category_delete_view_removes_data(self, client):
        category = Category.objects.create(name='Categoria Para Deletar', type=Category.Type.PRODUCT)
        url = reverse('catalog:category_delete', args=[category.id])
        
        # Testar confirmação (POST)
        response = client.post(url)
        assert response.status_code == 302 # Redirect após delete (ou 204 se for HTMX)
        
        # Se for HTMX request no teste, precisaria header HX-Request. 
        # A view implementada suporta both. Testando fluxo padrão.
        
        assert not Category.objects.filter(id=category.id).exists()
