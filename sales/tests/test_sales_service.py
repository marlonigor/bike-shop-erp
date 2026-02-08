import pytest
from decimal import Decimal
from sales.services import SalesService
from sales.models import Sale
from stock.services import StockService
from core.exceptions import InsufficientStockError
from core.models import Client

@pytest.fixture
def client(db):
    return Client.objects.create(name="João Silva", document="12345678901")

@pytest.mark.django_db
class TestSalesService:
    def test_create_sale_successful(self, client, warehouse, product):
        """Venda bem-sucedida deve reduzir o estoque e criar registros de venda."""
        # Arrange: Adicionar estoque inicial
        StockService.add_stock(product, warehouse, 10)
        
        items_data = [
            {'product': product, 'quantity': 3, 'unit_price': Decimal('100.00')}
        ]
        
        # Act
        sale = SalesService.create_sale(client, warehouse, items_data)
        
        # Assert
        assert sale.status == Sale.Status.COMPLETED
        assert sale.total_amount == Decimal('300.00')
        assert sale.items.count() == 1
        assert StockService.get_balance(product, warehouse) == 7

    def test_create_sale_insufficient_stock_raises_error(self, client, warehouse, product):
        """Venda com estoque insuficiente deve levantar erro e não criar venda (rollback)."""
        # Arrange: Estoque insuficiente
        StockService.add_stock(product, warehouse, 2)
        
        items_data = [
            {'product': product, 'quantity': 5, 'unit_price': Decimal('100.00')}
        ]
        
        # Act & Assert
        with pytest.raises(InsufficientStockError):
            SalesService.create_sale(client, warehouse, items_data)
            
        # Verificar que a venda não foi criada
        assert Sale.objects.count() == 0
        # Verificar que o estoque permaneceu o mesmo
        assert StockService.get_balance(product, warehouse) == 2

    def test_create_sale_multiple_items(self, client, warehouse, product, product_secondary):
        """Venda com múltiplos itens deve processar todos corretamente."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)
        StockService.add_stock(product_secondary, warehouse, 20)
        
        items_data = [
            {'product': product, 'quantity': 2, 'unit_price': Decimal('50.00')},
            {'product': product_secondary, 'quantity': 5, 'unit_price': Decimal('20.00')}
        ]
        
        # Act
        sale = SalesService.create_sale(client, warehouse, items_data)
        
        # Assert
        assert sale.total_amount == Decimal('200.00') # (2*50) + (5*20)
        assert StockService.get_balance(product, warehouse) == 8
        assert StockService.get_balance(product_secondary, warehouse) == 15
