import pytest
from django.urls import reverse

from customers.models import Customer


@pytest.mark.django_db
class TestCustomerViews:
    @pytest.fixture
    def customer(self):
        return Customer.objects.create(
            name='João da Silva',
            email='joao@example.com',
            phone='11999999999',
            document='12345678900',
            active=True,
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
            'active': True,
        }
        response = client.post(url, data)
        assert response.status_code == 302  # Redirect
        assert Customer.objects.filter(email='maria@example.com').exists()

    def test_customer_create_view_post_invalid_data(self, client):
        url = reverse('customers:customer_create')
        data = {
            'name': '',  # Nome obrigatório
            'email': 'inválido',
        }
        response = client.post(url, data)
        assert response.status_code == 200  # Fica na página com erro
        assert 'form' in response.context
        assert response.context['form'].errors['name']

    def test_customer_edit_view_updates_data(self, client, customer):
        url = reverse('customers:customer_edit', args=[customer.id])
        data = {
            'name': 'João da Silva Editado',
            'email': customer.email,
            'phone': customer.phone,
            'document': customer.document,
            'active': True,
        }
        response = client.post(url, data)
        assert response.status_code == 302

        customer.refresh_from_db()
        assert customer.name == 'João da Silva Editado'

    def test_customer_create_pdv_source_htmx_returns_option(self, client):
        url = reverse('customers:customer_create') + '?source=pdv'
        data = {
            'name': 'Carlos PDV',
            'phone': '11977777777',
            'active': True,
        }
        response = client.post(url, data, headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert 'Carlos PDV' in response.content.decode()
        assert 'customerCreated' in response.headers['HX-Trigger']
        assert Customer.objects.filter(name='Carlos PDV').exists()

    def test_customer_list_view_htmx_returns_partial(self, client, customer):
        url = reverse('customers:customer_list')
        response = client.get(url, headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert 'customers/partials/customer_table.html' in [t.name for t in response.templates]

    def test_customer_delete_view_soft_deletes(self, client, customer):
        url = reverse('customers:customer_delete', args=[customer.id])

        response = client.post(url)
        assert response.status_code == 302

        customer.refresh_from_db()
        assert customer.active is False

    def test_customer_delete_view_htmx_returns_204(self, client, customer):
        url = reverse('customers:customer_delete', args=[customer.id])
        response = client.post(url, headers={'HX-Request': 'true'})
        assert response.status_code == 204
        assert 'customerListChanged' in response.headers['HX-Trigger']

        customer.refresh_from_db()
        assert customer.active is False

    def test_customer_delete_with_associated_sales_soft_deletes_without_error(
        self, client, customer, warehouse, product
    ):
        from sales.models import Sale, SaleItem

        sale = Sale.objects.create(
            customer=customer,
            warehouse=warehouse,
            total_amount=product.price,
            status=Sale.Status.COMPLETED,
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=1,
            unit_price=product.price,
            total_price=product.price,
        )

        url = reverse('customers:customer_delete', args=[customer.id])
        response = client.post(url)
        assert response.status_code == 302

        customer.refresh_from_db()
        assert customer.active is False
