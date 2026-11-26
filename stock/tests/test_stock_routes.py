"""Regressões dos fluxos de estoque exercitados durante a adoção de tipos estritos."""

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Product
from stock.models import Stock, Warehouse


@pytest.mark.django_db
@pytest.mark.parametrize('partial', [False, True])
def test_stock_list_keeps_warehouse_and_low_stock_filters(
    client: Client, product: Product, warehouse: Warehouse, partial: bool
) -> None:
    """A seleção do depósito e o recorte de saldo baixo sobrevivem à renderização."""
    Stock.objects.create(product=product, warehouse=warehouse, quantity=3)
    headers = {'HTTP_HX_REQUEST': 'true'} if partial else {}
    response = client.get(
        reverse('stock:stock_list'),
        {
            'warehouse': str(warehouse.id),
            'low_stock': '1',
        },
        **headers,
    )

    assert response.status_code == 200
    assert response.context['selected_warehouse'] == str(warehouse.id)
    assert response.context['stocks'].count() == 1


@pytest.mark.django_db
def test_stock_movement_renders_the_initial_form(client: Client) -> None:
    """Mantém acessível o formulário antes de enviar uma movimentação."""
    assert client.get(reverse('stock:stock_movement')).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize('movement_type', ['IN', 'OUT'])
def test_stock_movement_updates_balance_and_returns_htmx_feedback(
    client: Client, product: Product, warehouse: Warehouse, movement_type: str
) -> None:
    """Entradas e saídas mantêm o retorno HTMX e a alteração transacional do saldo."""
    Stock.objects.create(product=product, warehouse=warehouse, quantity=10)
    response = client.post(
        reverse('stock:stock_movement'),
        {
            'product_id': str(product.id),
            'warehouse_id': str(warehouse.id),
            'quantity': '2',
            'movement_type': movement_type,
        },
        HTTP_HX_REQUEST='true',
    )

    assert response.status_code == 204
    assert 'stockListChanged' in response.headers['HX-Trigger']
    assert Stock.objects.get(product=product, warehouse=warehouse).quantity == (
        12 if movement_type == 'IN' else 8
    )


@pytest.mark.django_db
def test_stock_movement_keeps_errors_on_the_form(
    client: Client, product: Product, warehouse: Warehouse
) -> None:
    """Uma quantidade inválida permanece visível como erro, sem alterar o estoque."""
    response = client.post(
        reverse('stock:stock_movement'),
        {
            'product_id': str(product.id),
            'warehouse_id': str(warehouse.id),
            'quantity': 'invalid',
            'movement_type': 'IN',
        },
    )

    assert response.status_code == 400
    assert 'error' in response.context


@pytest.mark.django_db
def test_stock_adjust_rejects_invalid_data(client: Client) -> None:
    """Campos obrigatórios ausentes retornam o formulário com erros."""
    assert client.get(reverse('stock:stock_adjust')).status_code == 200
    response = client.post(reverse('stock:stock_adjust'), {})

    assert response.status_code == 200
    assert response.context['form'].errors


@pytest.mark.django_db
def test_stock_adjust_updates_the_exact_balance(
    client: Client, product: Product, warehouse: Warehouse
) -> None:
    """O formulário validado passa modelos e quantidade corretos ao ajuste."""
    response = client.post(
        reverse('stock:stock_adjust'),
        {
            'product': str(product.id),
            'warehouse': str(warehouse.id),
            'new_quantity': '7',
            'reason': 'Contagem de teste',
        },
    )

    assert response.status_code == 302
    assert Stock.objects.get(product=product, warehouse=warehouse).quantity == 7
