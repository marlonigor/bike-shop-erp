import pytest
from django.urls import reverse
from stock.models import Stock, StockMovement
from stock.services.stock_service import StockService

@pytest.mark.django_db
class TestStockAdjustment:
    def test_stock_adjustment_creates_movement_and_updates_balance(self, client, product, warehouse):
        # Setup: Estoque inicial
        StockService.add_stock(product, warehouse, 10, reason="Inicial")
        assert StockService.get_balance(product, warehouse) == 10
        
        # Action: Ajuste para 15 (Entrada de 5)
        url = reverse('stock:stock_adjust')
        data = {
            'warehouse': warehouse.id,
            'product': product.id,
            'new_quantity': 15,
            'reason': 'Contagem física'
        }
        
        response = client.post(url, data)
        assert response.status_code == 302 # Redirect
        
        # Assert: Saldo atualizado
        assert StockService.get_balance(product, warehouse) == 15
        
        # Assert: Movimento criado
        movement = StockMovement.objects.first() # Último criado (order by -created_at)
        assert movement.movement_type == StockMovement.MovementType.ADJUST
        assert movement.new_quantity == 15
        assert movement.quantity == 5 # Diferença absoluta
        
    def test_stock_adjustment_down_creates_movement(self, client, product, warehouse):
        # Setup: Estoque inicial
        StockService.add_stock(product, warehouse, 20, reason="Inicial")
        
        # Action: Ajuste para 18 (Saída de 2)
        url = reverse('stock:stock_adjust')
        data = {
            'warehouse': warehouse.id,
            'product': product.id,
            'new_quantity': 18,
            'reason': 'Perda'
        }
        
        response = client.post(url, data)
        assert response.status_code == 302
        
        # Assert
        assert StockService.get_balance(product, warehouse) == 18
        
        movement = StockMovement.objects.first()
        assert movement.movement_type == StockMovement.MovementType.ADJUST
        assert movement.new_quantity == 18
        assert movement.quantity == 2
