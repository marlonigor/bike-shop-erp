"""Confere legibilidade e adaptação do painel em Chromium isolado."""

from decimal import Decimal
from pathlib import Path

import pytest
from playwright.sync_api import Page, Route, expect
from pytest_django.live_server_helper import LiveServer

from catalog.models import Product
from customers.models import Customer
from sales.models import Sale, SaleItem
from stock.models import Stock, Warehouse


@pytest.fixture
def dashboard_sale(
    transactional_db: None, customer: Customer, warehouse: Warehouse, product: Product
) -> Sale:
    """Popula as três tabelas para detectar recortes que só ocorrem com dados."""
    sale = Sale.objects.create(
        customer=customer,
        warehouse=warehouse,
        total_amount=Decimal('1234.56'),
        status=Sale.Status.COMPLETED,
    )
    SaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=1,
        unit_price=Decimal('1234.56'),
        total_price=Decimal('1234.56'),
    )
    Stock.objects.create(product=product, warehouse=warehouse, quantity=3)
    return sale


def _block_external_asset(route: Route) -> None:
    route.abort()


def _open_dashboard(page: Page, url: str, width: int, theme: str) -> None:
    page.route('https://**/*', _block_external_asset)
    page.emulate_media(reduced_motion='reduce')
    page.set_viewport_size({'width': width, 'height': 900})
    page.goto(url, wait_until='domcontentloaded')
    page.evaluate(
        '(theme) => document.documentElement.classList.toggle("light", theme === "light")', theme
    )
    page.locator('.filters-bar').wait_for()
    background = 'rgb(255, 255, 255)' if theme == 'light' else 'rgb(26, 26, 62)'
    expect(page.locator('.stat-card').first).to_have_css('background-color', background)


def _text_contrast(page: Page, selector: str) -> float:
    return float(
        page.locator(selector).first.evaluate("""element => {
        const rgb = value => value.match(/[\\d.]+/g).slice(0, 3).map(Number);
        const luminance = value => rgb(value).map(channel => {
            const scaled = channel / 255;
            return scaled <= .04045 ? scaled / 12.92 : ((scaled + .055) / 1.055) ** 2.4;
        }).reduce((sum, channel, index) => sum + channel * [.2126, .7152, .0722][index], 0);
        const style = getComputedStyle(element);
        const background = getComputedStyle(element.closest('.stat-card, .card, form, .header, .sidebar'));
        const light = luminance(style.color);
        const dark = luminance(background.backgroundColor);
        return (Math.max(light, dark) + .05) / (Math.min(light, dark) + .05);
    }""")
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('theme', ['dark', 'light'])
def test_dashboard_has_readable_stat_values(
    live_server: LiveServer, browser_page: Page, theme: str, tmp_path: Path
) -> None:
    """Evita que os degradês decorativos escondam os indicadores."""
    _open_dashboard(browser_page, live_server.url, 1280, theme)
    value = browser_page.locator('.stat-value').first

    assert (
        value.evaluate('(element) => getComputedStyle(element).webkitTextFillColor')
        != 'rgba(0, 0, 0, 0)'
    )
    assert _text_contrast(browser_page, '.stat-value') >= 4.5
    assert _text_contrast(browser_page, '.stat-label') >= 4.5
    assert _text_contrast(browser_page, '.card-header .btn') >= 4.5
    assert _text_contrast(browser_page, '.empty-state.success') >= 4.5
    assert _text_contrast(browser_page, '.page-title') >= 4.5
    browser_page.screenshot(path=str(tmp_path / f'dashboard-{theme}.png'), full_page=True)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('width', [320, 390, 768, 1280])
def test_dashboard_fits_the_viewport(
    dashboard_sale: Sale, live_server: LiveServer, browser_page: Page, width: int, tmp_path: Path
) -> None:
    """Mantém filtros e cabeçalhos acessíveis sem rolagem da página para os lados."""
    _open_dashboard(browser_page, live_server.url, width, 'dark')
    expect(browser_page.get_by_role('button', name='Aplicar filtros')).to_be_in_viewport()
    assert browser_page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    expect(browser_page.get_by_role('region', name='Produtos mais vendidos')).to_be_visible()
    expect(browser_page.locator('.stat-value').first).to_have_text('R$ 1.234,56')
    browser_page.screenshot(path=str(tmp_path / f'dashboard-{width}.png'), full_page=True)


@pytest.mark.django_db(transaction=True)
def test_dashboard_applies_warehouse_and_keeps_touch_targets(
    dashboard_sale: Sale, live_server: LiveServer, browser_page: Page
) -> None:
    """Confere a ação principal no celular e a continuidade para o estoque."""
    _open_dashboard(browser_page, live_server.url, 390, 'light')
    browser_page.get_by_label('Depósito', exact=True).select_option(
        str(dashboard_sale.warehouse_id)
    )
    button = browser_page.get_by_role('button', name='Aplicar filtros')
    button.focus()
    browser_page.keyboard.press('Tab')
    browser_page.keyboard.press('Shift+Tab')
    expect(button).to_have_css('outline-width', '3px')
    assert button.evaluate('(element) => element.getBoundingClientRect().height') >= 44
    button.click()
    expect(browser_page.get_by_role('link', name='Ver Todos', exact=True)).to_have_attribute(
        'href', f'/estoque/?low_stock=1&warehouse={dashboard_sale.warehouse_id}'
    )
