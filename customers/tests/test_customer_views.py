import pytest
from django.urls import reverse
from customers.models import Customer
from customers.forms import CustomerForm

@pytest.mark.django_db
class TestCustomerViews:
    
    @pytest.fixture
    def customer(self):
        return Customer.objects.create(
            name='João da Silva',
            email='joao@example.com',
            phone='11999999999',
            document='12345678900',
            active=True
        )

    def test_customer_list_view_returns_200(self, client, customer):
        url = reverse('customers:customer_list')
        response = client.get(url)
        assert response.status_code == 200
        assert customer in response.context['customers']
        assert 'customers/customer_list.html' in [t.name for t in response.templates]

    def test_customer_create_view_post_valid_data(self, client):
        url = reverse('customers:customer_create')
        data = {
            'name': 'Maria Souza',
            'email': 'maria@example.com',
            'phone': '11888888888',
            'document': '98765432100',
            'active': True
        }
        response = client.post(url, data)
        assert response.status_code == 302 # Redirect
        assert Customer.objects.filter(email='maria@example.com').exists()

    def test_customer_create_view_post_invalid_data(self, client):
        url = reverse('customers:customer_create')
        data = {
            'name': '', # Nome obrigatório
            'email': 'inválido'
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors['name']

    def test_customer_edit_view_updates_data(self, client, customer):
        url = reverse('customers:customer_edit', args=[customer.id])
        data = {
            'name': 'João da Silva Editado',
            'email': customer.email,
            'phone': customer.phone,
            'document': customer.document,
            'active': True
        }
        response = client.post(url, data)
        assert response.status_code == 302
        
        customer.refresh_from_db()
        assert customer.name == 'João da Silva Editado'

    def test_customer_delete_view_removes_data(self, client, customer):
        url = reverse('customers:customer_delete', args=[customer.id])
        
        response = client.post(url)
        assert response.status_code == 302
        
        assert not Customer.objects.filter(id=customer.id).exists()
