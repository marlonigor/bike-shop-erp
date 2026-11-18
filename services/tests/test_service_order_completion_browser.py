"""Cenarios de navegador para a confirmacao de conclusao da oficina."""

import pytest
from django.urls import reverse
from playwright.sync_api import Locator, Page, expect
from pytest_django.live_server_helper import LiveServer

from customers.models import Customer
from services.models import ServiceOrder
from stock.models import Warehouse


@pytest.fixture
def in_progress_order(
    transactional_db: None, customer: Customer, warehouse: Warehouse
) -> ServiceOrder:
    """Cria uma OS pronta para validar a confirmacao em um navegador real."""
    return ServiceOrder.objects.create(
        customer=customer,
        warehouse=warehouse,
        bike_description='Bicicleta de teste E2E',
        client_reported_defect='Validar confirmacao da conclusao',
        status=ServiceOrder.Status.IN_PROGRESS,
    )


def _open_completion_modal(page: Page, order_url: str) -> Locator:
    page.goto(order_url)
    page.get_by_role('button', name='Concluir Manutenção').click()
    return page.get_by_role('dialog', name='Concluir manutenção?')


@pytest.mark.django_db(transaction=True)
def test_completion_modal_receives_focus(
    in_progress_order: ServiceOrder, live_server: LiveServer, browser_page: Page
) -> None:
    """Garante que o dialogo receba foco quando a confirmacao e aberta."""
    order_url = (
        f'{live_server.url}{reverse("services:service_order_detail", args=[in_progress_order.id])}'
    )
    modal = _open_completion_modal(browser_page, order_url)

    expect(modal).to_be_visible()
    assert modal.evaluate('(element) => document.activeElement === element') is True


@pytest.mark.django_db(transaction=True)
def test_escape_closes_completion_modal(
    in_progress_order: ServiceOrder, live_server: LiveServer, browser_page: Page
) -> None:
    """Permite abandonar a confirmacao sem alterar o status da OS."""
    order_url = (
        f'{live_server.url}{reverse("services:service_order_detail", args=[in_progress_order.id])}'
    )
    modal = _open_completion_modal(browser_page, order_url)

    browser_page.keyboard.press('Escape')

    expect(modal).to_be_hidden()
    expect(browser_page.get_by_text('STATUS ATUAL: EM MANUTENÇÃO', exact=False)).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_confirming_completion_updates_service_order(
    in_progress_order: ServiceOrder, live_server: LiveServer, browser_page: Page
) -> None:
    """Conclui a OS apenas apos a pessoa confirmar o dialogo acessivel."""
    order_url = (
        f'{live_server.url}{reverse("services:service_order_detail", args=[in_progress_order.id])}'
    )
    _open_completion_modal(browser_page, order_url)

    browser_page.get_by_role('button', name='Confirmar conclusão').click()

    expect(browser_page.get_by_text('CONCLUÍDA (PRONTA)', exact=False)).to_be_visible()
