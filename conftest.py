"""
Fixtures compartilhadas para testes do Bike Shop ERP.
"""

from collections.abc import Generator
from decimal import Decimal

import pytest
from playwright.sync_api import Browser, Page, sync_playwright


@pytest.fixture
def chromium_browser() -> Generator[Browser, None, None]:
    """Inicia Chromium isolado para os testes E2E em modo headless."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def browser_page(chromium_browser: Browser) -> Generator[Page, None, None]:
    """Entrega uma pagina limpa e a encerra ao terminar cada teste E2E."""
    browser_page = chromium_browser.new_page()
    try:
        yield browser_page
    finally:
        browser_page.close()


@pytest.fixture
def warehouse(db):
    """Cria um depósito para testes."""
    from stock.models import Warehouse

    return Warehouse.objects.create(name='Depósito Principal', location='Galpão A')


@pytest.fixture
def warehouse_secondary(db):
    """Cria um segundo depósito para testes de múltiplos depósitos."""
    from stock.models import Warehouse

    return Warehouse.objects.create(name='Depósito Secundário', location='Galpão B')


@pytest.fixture
def category(db):
    """Cria uma categoria para testes."""
    from catalog.models import Category

    return Category.objects.create(name='Peças')


@pytest.fixture
def product(db, category):
    """Cria um produto para testes."""
    from catalog.models import Product

    return Product.objects.create(
        sku='PNEU-001',
        name='Pneu Aro 29',
        category=category,
        cost=Decimal('50.00'),
        price=Decimal('80.00'),
    )


@pytest.fixture
def product_secondary(db, category):
    """Cria um segundo produto para testes."""
    from catalog.models import Product

    return Product.objects.create(
        sku='CAMARA-001',
        name='Câmara de Ar 29',
        category=category,
        cost=Decimal('15.00'),
        price=Decimal('25.00'),
    )


@pytest.fixture
def customer(db):
    """Cria um cliente ativo para testes."""
    from customers.models import Customer

    return Customer.objects.create(
        name='Cliente Padrão Teste',
        email='cliente@exemplo.com',
        phone='11987654321',
        document='12345678901',
        active=True,
    )


@pytest.fixture
def client_db(customer):
    """Alias retrocompativel para testes legados que usavam client_db."""
    return customer
