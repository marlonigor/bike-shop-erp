"""Testes do comando para popular um ambiente local de demonstracao."""

from io import StringIO

import pytest
from django.core.management import call_command

from catalog.models import Product
from customers.models import Customer
from sales.models import Sale
from services.models import ServiceOrder
from stock.models import Stock, Warehouse


@pytest.mark.django_db
def test_seed_demo_data_creates_idempotent_demo_entities() -> None:
    """Cria dados conectados sem duplicar a massa ao executar novamente."""
    output = StringIO()

    call_command('seed_demo_data', stdout=output)
    call_command('seed_demo_data', stdout=output)

    store = Warehouse.objects.get(name='[DEMO] Loja Centro')
    tire = Product.objects.get(sku='DEMO-TIRE-29')
    active_order = ServiceOrder.objects.get(notes='[DEMO] OS em manutenção')

    assert Customer.objects.filter(email__endswith='@example.test').count() == 3
    assert Product.objects.filter(sku__startswith='DEMO-').count() == 6
    assert Sale.objects.filter(notes__startswith='[DEMO]').count() == 2
    assert active_order.status == ServiceOrder.Status.IN_PROGRESS
    assert Stock.objects.get(product=tire, warehouse=store).quantity == 12
    assert 'Massa de demonstracao pronta.' in output.getvalue()
