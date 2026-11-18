"""Regression checks for accessible templates and design-system safeguards."""

from pathlib import Path

from django.template.loader import get_template

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_project_file(relative_path: str) -> str:
    """Return UTF-8 source content for a project asset.

    Example:
        source = _read_project_file('templates/base.html')
    """
    return (PROJECT_ROOT / relative_path).read_text(encoding='utf-8')


def test_base_template_exposes_keyboard_navigation_landmarks() -> None:
    """Keep skip navigation and named navigation available to keyboard users."""
    source = _read_project_file('templates/base.html')

    assert 'class="skip-link" href="#main-content"' in source
    assert 'aria-label="Navegação principal"' in source
    assert 'aria-label="Abrir menu de navegação"' in source


def test_base_template_announces_toasts_and_names_close_action() -> None:
    """Ensure transient feedback is announced and can be dismissed accessibly."""
    source = _read_project_file('templates/base.html')

    assert 'aria-live="polite"' in source
    assert "closeBtn.setAttribute('aria-label', 'Fechar notificação')" in source


def test_design_system_provides_focus_motion_and_touch_guards() -> None:
    """Prevent regressions in focus visibility, motion reduction, and touch targets."""
    source = _read_project_file('static/css/accessibility.css')

    assert ':focus-visible' in source
    assert 'prefers-reduced-motion: reduce' in source
    assert '.btn-remove' in source
    assert 'width: 44px;' in source


def test_base_template_compiles_with_django() -> None:
    """Keep base template syntax valid before a browser renders navigation.

    Example:
        template = get_template('base.html')
    """
    assert get_template('base.html')
