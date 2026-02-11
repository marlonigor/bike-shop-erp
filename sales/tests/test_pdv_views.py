import pytest
from decimal import Decimal
from django.urls import reverse


@pytest.fixture
def client_db(db):
    from core.models import Client
    return Client.objects.create(name="Cliente Teste PDV", document="99988877766")


@pytest.mark.django_db
class TestCartRemove:
    def test_cart_remove_removes_item(self, client, product):
        """Remove um item existente do carrinho."""
        # Adicionar item ao carrinho
        client.post(reverse('sales:cart_add'), {
            'product_id': str(product.id),
            'quantity': 2,
        })
        assert len(client.session['cart']) == 1

        # Remover item
        response = client.post(reverse('sales:cart_remove'), {
            'product_id': str(product.id),
        })
        assert response.status_code == 200
        assert len(client.session['cart']) == 0

    def test_cart_remove_nonexistent_returns_200(self, client):
        """Remover um item que não existe retorna 200 (graceful)."""
        response = client.post(reverse('sales:cart_remove'), {
            'product_id': '99999',
        })
        assert response.status_code == 200


@pytest.mark.django_db
class TestCartUpdate:
    def test_cart_update_changes_quantity(self, client, product):
        """Atualizar quantidade recalcula o total."""
        client.post(reverse('sales:cart_add'), {
            'product_id': str(product.id),
            'quantity': 1,
        })

        response = client.post(reverse('sales:cart_update'), {
            'product_id': str(product.id),
            'quantity': 5,
        })
        assert response.status_code == 200

        cart = client.session['cart']
        assert cart[0]['quantity'] == 5
        assert cart[0]['total'] == str(product.price * 5)

    def test_cart_update_invalid_quantity_returns_400(self, client, product):
        """Quantidade <= 0 retorna 400."""
        client.post(reverse('sales:cart_add'), {
            'product_id': str(product.id),
            'quantity': 1,
        })

        response = client.post(reverse('sales:cart_update'), {
            'product_id': str(product.id),
            'quantity': 0,
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestCartClear:
    def test_cart_clear_empties_cart(self, client, product):
        """Limpar carrinho remove todos os itens."""
        # Adicionar 2 itens
        client.post(reverse('sales:cart_add'), {
            'product_id': str(product.id),
            'quantity': 3,
        })

        response = client.post(reverse('sales:cart_clear'))
        assert response.status_code == 200
        assert client.session['cart'] == []


@pytest.mark.django_db
class TestSaleCompleteValidation:
    def test_sale_complete_without_client_returns_400(self, client, product, warehouse):
        """Finalizar sem cliente retorna 400."""
        from stock.services import StockService
        StockService.add_stock(product, warehouse, 10)

        client.post(reverse('sales:cart_add'), {
            'product_id': str(product.id),
            'quantity': 1,
        })

        response = client.post(reverse('sales:sale_complete'), {
            'warehouse_id': str(warehouse.id),
            # client_id omitido
        })
        assert response.status_code == 400
        assert 'Selecione cliente' in response.content.decode()

    def test_sale_complete_without_warehouse_returns_400(self, client, client_db, product):
        """Finalizar sem depósito retorna 400."""
        client.post(reverse('sales:cart_add'), {
            'product_id': str(product.id),
            'quantity': 1,
        })

        response = client.post(reverse('sales:sale_complete'), {
            'client_id': str(client_db.id),
            # warehouse_id omitido
        })
        assert response.status_code == 400
        assert 'Selecione cliente' in response.content.decode()
