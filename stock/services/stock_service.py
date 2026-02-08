"""
StockService - Serviço centralizado para gestão de estoque.

Este serviço encapsula toda a lógica de movimentação de estoque,
garantindo rastreabilidade e validação de regras de negócio.
"""

from django.db import transaction

from core.exceptions import InsufficientStockError
from stock.models import Stock, StockMovement, Warehouse
from catalog.models import Product


class StockService:
    """
    Serviço para operações de estoque.
    
    Todas as operações criam StockMovement, e o signal post_save
    atualiza automaticamente o saldo na tabela Stock.
    """

    @staticmethod
    @transaction.atomic
    def add_stock(
        product: Product,
        warehouse: Warehouse,
        quantity: int,
        reference_type: str = StockMovement.ReferenceType.MANUAL,
        reference_id=None,
        reason: str = "",
    ) -> StockMovement:
        """
        Adiciona estoque (entrada).

        Args:
            product: Produto a ser adicionado
            warehouse: Depósito destino
            quantity: Quantidade a adicionar (deve ser > 0)
            reference_type: Tipo de referência (PURCHASE, SALE, etc.)
            reference_id: UUID da referência (PurchaseOrder, Sale, etc.)
            reason: Motivo da movimentação

        Returns:
            StockMovement criado

        Raises:
            ValueError: Se quantity <= 0
        """
        if quantity <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            movement_type=StockMovement.MovementType.IN,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
        )
        return movement

    @staticmethod
    @transaction.atomic
    def remove_stock(
        product: Product,
        warehouse: Warehouse,
        quantity: int,
        reference_type: str = StockMovement.ReferenceType.MANUAL,
        reference_id=None,
        reason: str = "",
    ) -> StockMovement:
        """
        Remove estoque (saída).

        Args:
            product: Produto a ser removido
            warehouse: Depósito origem
            quantity: Quantidade a remover (deve ser > 0)
            reference_type: Tipo de referência
            reference_id: UUID da referência
            reason: Motivo da movimentação

        Returns:
            StockMovement criado

        Raises:
            ValueError: Se quantity <= 0
            InsufficientStockError: Se estoque insuficiente
        """
        if quantity <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        # Verifica disponibilidade antes de criar movimento
        available = StockService.get_balance(product, warehouse)
        if available < quantity:
            raise InsufficientStockError(
                product=product,
                warehouse=warehouse,
                requested=quantity,
                available=available,
            )

        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=quantity,
            movement_type=StockMovement.MovementType.OUT,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
        )
        return movement

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        product: Product,
        warehouse: Warehouse,
        new_quantity: int,
        reason: str = "",
    ) -> StockMovement | None:
        """
        Ajusta estoque para um valor exato.

        Cria uma movimentação IN ou OUT conforme a diferença
        entre o saldo atual e o novo saldo desejado.

        Args:
            product: Produto a ajustar
            warehouse: Depósito
            new_quantity: Novo saldo desejado (>= 0)
            reason: Motivo do ajuste

        Returns:
            StockMovement criado, ou None se não houver diferença

        Raises:
            ValueError: Se new_quantity < 0
        """
        if new_quantity < 0:
            raise ValueError("Quantidade não pode ser negativa")

        current = StockService.get_balance(product, warehouse)
        diff = new_quantity - current

        if diff == 0:
            return None

        movement = StockMovement.objects.create(
            product=product,
            warehouse=warehouse,
            quantity=abs(diff),
            movement_type=StockMovement.MovementType.ADJUST,
            new_quantity=new_quantity,
            reference_type=StockMovement.ReferenceType.MANUAL,
            reason=reason or f"Ajuste de estoque: {current} -> {new_quantity}",
        )
        return movement

    @staticmethod
    def get_balance(product: Product, warehouse: Warehouse) -> int:
        """
        Retorna o saldo atual de um produto em um depósito.

        Args:
            product: Produto
            warehouse: Depósito

        Returns:
            Quantidade em estoque (0 se não existir registro)
        """
        try:
            stock = Stock.objects.get(product=product, warehouse=warehouse)
            return stock.quantity
        except Stock.DoesNotExist:
            return 0

    @staticmethod
    def check_availability(
        product: Product, warehouse: Warehouse, quantity: int
    ) -> bool:
        """
        Verifica se há estoque suficiente para uma operação.

        Args:
            product: Produto
            warehouse: Depósito
            quantity: Quantidade desejada

        Returns:
            True se quantidade disponível >= quantidade solicitada
        """
        return StockService.get_balance(product, warehouse) >= quantity
