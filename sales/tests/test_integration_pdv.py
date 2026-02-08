import pytest
from django.urls import reverse
from decimal import Decimal
from sales.models import Sale, SaleItem
from stock.models import Stock
from core.models import Client
from stock.services import StockService

@pytest.fixture
def client_db(db):
    return Client.objects.create(name="Cliente Teste E2E", document="12345678901")

@pytest.mark.django_db
class TestSaleIntegration:
    def test_complete_sale_flow_e2e(self, client, client_db, warehouse, product):
        """
        Testa o fluxo completo de uma venda via PDV:
        1. Adição ao carrinho via POST
        2. Finalização da venda via POST
        3. Validação de dados e estoque
        """
        # 1. Preparar o estoque (10 unidades)
        StockService.add_stock(product, warehouse, 10)
        
        # 2. Adicionar produto ao carrinho
        url_add = reverse('sales:cart_add')
        response_add = client.post(url_add, {
            'product_id': str(product.id),
            'quantity': 2
        })
        assert response_add.status_code == 200
        
        # Verificar se o item está na sessão
        session = client.session
        assert 'cart' in session
        assert len(session['cart']) == 1
        assert session['cart'][0]['product_id'] == str(product.id)
        assert session['cart'][0]['quantity'] == 2
        
        # 3. Finalizar a venda
        url_complete = reverse('sales:sale_complete')
        response_complete = client.post(url_complete, {
            'client_id': str(client_db.id),
            'warehouse_id': str(warehouse.id)
        })
        assert response_complete.status_code == 200
        
        # 4. Validar resultados no banco de dados
        # Venda criada?
        sale = Sale.objects.first()
        assert sale is not None
        assert sale.client == client_db
        assert sale.total_amount == product.price * 2
        assert sale.status == Sale.Status.COMPLETED
        
        # Item de venda criado?
        sale_item = SaleItem.objects.all()[0]
        assert sale_item.product == product
        assert sale_item.quantity == 2
        
        # Estoque reduzido? (10 - 2 = 8)
        assert StockService.get_balance(product, warehouse) == 8
        
        # Carrinho limpo?
        assert client.session.get('cart') == []

    def test_sale_with_insufficient_stock_fails(self, client, client_db, warehouse, product):
        """
        Testa que a venda falha se não houver estoque suficiente no momento da finalização.
        """
        # 1. Adicionar apenas 1 unidade ao estoque
        StockService.add_stock(product, warehouse, 1)
        
        # 2. Tentar comprar 5 unidades
        client.post(reverse('sales:cart_add'), {
            'product_id': str(product.id),
            'quantity': 5
        })
        
        # 3. Finalizar a venda
        response = client.post(reverse('sales:sale_complete'), {
            'client_id': str(client_db.id),
            'warehouse_id': str(warehouse.id)
        })
        
        # 4. Validar erro (HttpResponse 400 conforme views.py)
        assert response.status_code == 400
        assert "Erro:" in response.content.decode()
        
        # Garantir que nenhuma venda foi criada e o estoque continua o mesmo
        assert Sale.objects.count() == 0
        assert StockService.get_balance(product, warehouse) == 1
