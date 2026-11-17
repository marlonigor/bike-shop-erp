"""Regression checks for preserving related HTMX filter values."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_template(relative_path: str) -> str:
    """Return a template source file for HTMX wiring assertions.

    Example:
        source = _read_template('templates/catalog/product_list.html')
    """
    return (PROJECT_ROOT / relative_path).read_text(encoding='utf-8')


def test_product_filters_include_search_and_category_together() -> None:
    """Keep the catalog category when an operator refines the text search."""
    source = _read_template('templates/catalog/product_list.html')

    assert 'hx-include="[name=\'category\']"' in source
    assert 'hx-include="[name=\'q\']"' in source


def test_stock_filters_include_warehouse_and_low_stock_together() -> None:
    """Keep both inventory constraints active when either control changes."""
    source = _read_template('templates/stock/stock_list.html')

    assert 'hx-include="[name=\'low_stock\']"' in source
    assert 'hx-include="[name=\'warehouse\']"' in source


def test_service_order_search_keeps_the_selected_status() -> None:
    """Keep the active service-order status while the operator searches."""
    source = _read_template('templates/services/service_order_list.html')

    assert 'type="hidden" name="status" x-model="currentStatus"' in source
    assert 'hx-include="[name=\'status\']"' in source
