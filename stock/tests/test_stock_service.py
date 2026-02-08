"""
Testes unitários para o StockService.

Este módulo testa todas as operações do serviço de estoque:
- Entrada (add_stock)
- Saída (remove_stock) 
- Ajuste (adjust_stock)
- Consulta de saldo (get_balance)
- Verificação de disponibilidade (check_availability)
"""

import pytest
import uuid

from core.exceptions import InsufficientStockError
from stock.models import Stock, StockMovement
from stock.services import StockService


class TestAddStock:
    """Testes para StockService.add_stock()"""

    def test_add_stock_increments_balance(self, product, warehouse):
        """Entrada deve incrementar o saldo."""
        # Act
        StockService.add_stock(product, warehouse, 10, reason="Compra inicial")

        # Assert
        assert StockService.get_balance(product, warehouse) == 10

    def test_add_stock_creates_movement(self, product, warehouse):
        """Entrada deve criar uma movimentação IN."""
        # Act
        movement = StockService.add_stock(product, warehouse, 5, reason="Teste")

        # Assert
        assert movement.movement_type == StockMovement.MovementType.IN
        assert movement.quantity == 5
        assert movement.product == product
        assert movement.warehouse == warehouse

    def test_add_stock_with_reference(self, product, warehouse):
        """Entrada com referência deve rastrear origem."""
        # Arrange
        ref_id = uuid.uuid4()

        # Act
        movement = StockService.add_stock(
            product,
            warehouse,
            10,
            reference_type=StockMovement.ReferenceType.PURCHASE,
            reference_id=ref_id,
        )

        # Assert
        assert movement.reference_type == StockMovement.ReferenceType.PURCHASE
        assert movement.reference_id == ref_id

    def test_add_stock_zero_raises_error(self, product, warehouse):
        """Entrada com quantidade zero deve levantar erro."""
        with pytest.raises(ValueError, match="maior que zero"):
            StockService.add_stock(product, warehouse, 0)

    def test_add_stock_negative_raises_error(self, product, warehouse):
        """Entrada com quantidade negativa deve levantar erro."""
        with pytest.raises(ValueError, match="maior que zero"):
            StockService.add_stock(product, warehouse, -5)


class TestRemoveStock:
    """Testes para StockService.remove_stock()"""

    def test_remove_stock_decrements_balance(self, product, warehouse):
        """Saída deve decrementar o saldo."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)

        # Act
        StockService.remove_stock(product, warehouse, 3, reason="Venda")

        # Assert
        assert StockService.get_balance(product, warehouse) == 7

    def test_remove_stock_insufficient_raises_error(self, product, warehouse):
        """Saída maior que saldo deve levantar InsufficientStockError."""
        # Arrange
        StockService.add_stock(product, warehouse, 5)

        # Act & Assert
        with pytest.raises(InsufficientStockError) as exc_info:
            StockService.remove_stock(product, warehouse, 10)

        assert exc_info.value.requested == 10
        assert exc_info.value.available == 5

    def test_remove_stock_creates_movement(self, product, warehouse):
        """Saída deve criar uma movimentação OUT."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)

        # Act
        movement = StockService.remove_stock(
            product, warehouse, 3, reason="Venda balcão"
        )

        # Assert
        assert movement.movement_type == StockMovement.MovementType.OUT
        assert movement.quantity == 3


class TestAdjustStock:
    """Testes para StockService.adjust_stock()"""

    def test_adjust_stock_sets_exact_balance(self, product, warehouse):
        """Ajuste deve definir saldo exato."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)

        # Act
        StockService.adjust_stock(product, warehouse, 15, reason="Inventário")

        # Assert
        assert StockService.get_balance(product, warehouse) == 15

    def test_adjust_stock_to_zero(self, product, warehouse):
        """Ajuste para zero deve zerar o saldo."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)

        # Act
        StockService.adjust_stock(product, warehouse, 0, reason="Zerado inventário")

        # Assert
        assert StockService.get_balance(product, warehouse) == 0

    def test_adjust_stock_no_change_returns_none(self, product, warehouse):
        """Ajuste sem diferença não deve criar movimentação."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)

        # Act
        result = StockService.adjust_stock(product, warehouse, 10)

        # Assert
        assert result is None

    def test_adjust_stock_negative_raises_error(self, product, warehouse):
        """Ajuste para valor negativo deve levantar erro."""
        with pytest.raises(ValueError, match="não pode ser negativa"):
            StockService.adjust_stock(product, warehouse, -5)


class TestGetBalance:
    """Testes para StockService.get_balance()"""

    def test_get_balance_no_stock_returns_zero(self, product, warehouse):
        """Saldo de produto sem estoque deve retornar 0."""
        # Act
        balance = StockService.get_balance(product, warehouse)

        # Assert
        assert balance == 0

    def test_get_balance_after_operations(self, product, warehouse):
        """Saldo deve refletir operações realizadas."""
        # Arrange
        StockService.add_stock(product, warehouse, 100)
        StockService.remove_stock(product, warehouse, 30)
        StockService.add_stock(product, warehouse, 10)

        # Act
        balance = StockService.get_balance(product, warehouse)

        # Assert
        assert balance == 80


class TestCheckAvailability:
    """Testes para StockService.check_availability()"""

    def test_check_availability_sufficient(self, product, warehouse):
        """Disponibilidade suficiente deve retornar True."""
        # Arrange
        StockService.add_stock(product, warehouse, 10)

        # Act & Assert
        assert StockService.check_availability(product, warehouse, 5) is True
        assert StockService.check_availability(product, warehouse, 10) is True

    def test_check_availability_insufficient(self, product, warehouse):
        """Disponibilidade insuficiente deve retornar False."""
        # Arrange
        StockService.add_stock(product, warehouse, 5)

        # Act & Assert
        assert StockService.check_availability(product, warehouse, 10) is False

    def test_check_availability_no_stock(self, product, warehouse):
        """Sem estoque deve retornar False para qualquer quantidade."""
        assert StockService.check_availability(product, warehouse, 1) is False


class TestMultipleWarehouses:
    """Testes para operações em múltiplos depósitos."""

    def test_multiple_warehouses_independent(
        self, product, warehouse, warehouse_secondary
    ):
        """Estoques em depósitos diferentes devem ser independentes."""
        # Act
        StockService.add_stock(product, warehouse, 100)
        StockService.add_stock(product, warehouse_secondary, 50)

        # Assert
        assert StockService.get_balance(product, warehouse) == 100
        assert StockService.get_balance(product, warehouse_secondary) == 50

    def test_remove_from_one_warehouse_not_affects_other(
        self, product, warehouse, warehouse_secondary
    ):
        """Remover de um depósito não deve afetar outro."""
        # Arrange
        StockService.add_stock(product, warehouse, 100)
        StockService.add_stock(product, warehouse_secondary, 100)

        # Act
        StockService.remove_stock(product, warehouse, 30)

        # Assert
        assert StockService.get_balance(product, warehouse) == 70
        assert StockService.get_balance(product, warehouse_secondary) == 100


class TestMovementTraceability:
    """Testes para rastreabilidade de movimentações."""

    def test_movement_traceability(self, product, warehouse):
        """Movimentações devem registrar origem e motivo."""
        # Arrange
        sale_id = uuid.uuid4()

        # Act
        StockService.add_stock(product, warehouse, 50, reason="Compra fornecedor ABC")
        movement = StockService.remove_stock(
            product,
            warehouse,
            10,
            reference_type=StockMovement.ReferenceType.SALE,
            reference_id=sale_id,
            reason="Venda #123",
        )

        # Assert
        assert movement.reference_type == StockMovement.ReferenceType.SALE
        assert movement.reference_id == sale_id
        assert movement.reason == "Venda #123"

        # Verificar que podemos rastrear movimentos
        movements = StockMovement.objects.filter(
            product=product, reference_type=StockMovement.ReferenceType.SALE
        )
        assert movements.count() == 1
        assert movements.first().reference_id == sale_id
