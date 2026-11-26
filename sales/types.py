"""Contratos do carrinho e da venda; exemplo: SaleItemInput com produto e quantidade."""

from decimal import Decimal
from typing import TypedDict

from catalog.models import Product


class SaleItemInput(TypedDict):
    """Item de entrada do faturamento, com preço decimal e produto já localizado."""

    product: Product
    quantity: int
    unit_price: Decimal


class CartItem(TypedDict):
    """Representação serializável de um item guardado na sessão do PDV."""

    product_id: str
    sku: str
    name: str
    quantity: int
    unit_price: str
    total: str
