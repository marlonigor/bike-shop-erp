"""
Fixtures compartilhadas para testes do Bike Shop ERP.
"""

import pytest
from decimal import Decimal


@pytest.fixture
def warehouse(db):
    """Cria um depósito para testes."""
    from stock.models import Warehouse
    return Warehouse.objects.create(
        name="Depósito Principal",
        location="Galpão A"
    )


@pytest.fixture
def warehouse_secondary(db):
    """Cria um segundo depósito para testes de múltiplos depósitos."""
    from stock.models import Warehouse
    return Warehouse.objects.create(
        name="Depósito Secundário",
        location="Galpão B"
    )


@pytest.fixture
def category(db):
    """Cria uma categoria para testes."""
    from catalog.models import Category
    return Category.objects.create(
        name="Peças"
    )


@pytest.fixture
def product(db, category):
    """Cria um produto para testes."""
    from catalog.models import Product
    return Product.objects.create(
        sku="PNEU-001",
        name="Pneu Aro 29",
        category=category,
        cost=Decimal("50.00"),
        price=Decimal("80.00"),
    )


@pytest.fixture
def product_secondary(db, category):
    """Cria um segundo produto para testes."""
    from catalog.models import Product
    return Product.objects.create(
        sku="CAMARA-001",
        name="Câmara de Ar 29",
        category=category,
        cost=Decimal("15.00"),
        price=Decimal("25.00"),
    )
