"""Regressões de apresentação do painel, sem depender da massa local."""

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from customers.models import Customer
from sales.models import Sale
from stock.models import Warehouse


@pytest.mark.django_db
def test_dashboard_formats_currency_in_brazilian_portuguese(
    client: Client, customer: Customer, warehouse: Warehouse
) -> None:
    """Mostra milhares e centavos locais mesmo com o projeto em inglês."""
    Sale.objects.create(
        customer=customer,
        warehouse=warehouse,
        total_amount=Decimal('1234.56'),
        status=Sale.Status.COMPLETED,
    )
    response = client.get(reverse('dashboard'))

    # Total, última venda, faturamento comparativo e ticket médio usam a mesma moeda.
    assert response.content.decode().count('R$ 1.234,56') == 4
