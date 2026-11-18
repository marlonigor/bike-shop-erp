"""Testes de regressão para a preservação de filtros relacionados no HTMX."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_template(relative_path: str) -> str:
    """Retorna o código-fonte de um template para validar a integração com HTMX.

    Exemplo:
        source = _read_template('templates/catalog/product_list.html')
    """
    return (PROJECT_ROOT / relative_path).read_text(encoding='utf-8')


def test_product_filter_form_submits_all_catalog_values() -> None:
    """Mantém busca, categoria, preço e disponibilidade na mesma requisição."""
    source = _read_template('templates/catalog/product_list.html')

    assert 'id="product-filters"' in source
    assert 'hx-get="{% url \'catalog:product_list\' %}"' in source
    assert 'name="min_price"' in source
    assert 'name="max_price"' in source
    assert 'name="availability"' in source


def test_stock_filters_include_warehouse_and_low_stock_together() -> None:
    """Mantém as duas restrições de inventário ao alterar qualquer controle."""
    source = _read_template('templates/stock/stock_list.html')

    assert 'hx-include="[name=\'low_stock\']"' in source
    assert 'hx-include="[name=\'warehouse\']"' in source


def test_service_order_search_keeps_the_selected_status() -> None:
    """Mantém o status ativo da ordem de serviço durante a busca."""
    source = _read_template('templates/services/service_order_list.html')

    assert 'type="hidden" name="status" x-model="currentStatus"' in source
    assert 'hx-include="[name=\'status\']"' in source
