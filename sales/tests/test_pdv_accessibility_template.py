"""Regression checks for accessible point-of-sale template behavior."""

from pathlib import Path

from django.template.loader import get_template

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_pdv_template() -> str:
    """Return point-of-sale template source for semantic regression checks.

    Example:
        source = _read_pdv_template()
    """
    return (PROJECT_ROOT / 'templates/sales/pdv.html').read_text(encoding='utf-8')


def test_pdv_template_uses_labeled_modal_dialogs() -> None:
    """Keep sale confirmation and customer creation accessible by keyboard."""
    source = _read_pdv_template()

    assert 'role="dialog"' in source
    assert 'aria-modal="true"' in source
    assert 'for="warehouse-select"' in source
    assert 'for="client-select"' in source


def test_pdv_templates_compile_with_django() -> None:
    """Keep dynamic point-of-sale templates valid for server rendering.

    Example:
        template = get_template('sales/pdv.html')
    """
    assert get_template('sales/pdv.html')
    assert get_template('customers/partials/pdv_customer_form.html')
