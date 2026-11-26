"""Garante que o comando inicial continue idempotente após receber tipagem."""

from io import StringIO

import pytest
from django.core.management import call_command

from catalog.models import Category, Product
from stock.models import Warehouse


@pytest.mark.django_db
def test_populate_command_keeps_initial_entities_unique() -> None:
    """Executar duas vezes mantém um serviço e as categorias de inicialização."""
    output = StringIO()
    call_command('populate_db', stdout=output)
    call_command('populate_db', stdout=output)

    assert Category.objects.count() == 2
    assert Warehouse.objects.filter(name='Loja Principal').count() == 1
    product = Product.objects.get(sku='SERV001')
    assert product.is_service is True
    assert 'Concluído com Sucesso' in output.getvalue()
