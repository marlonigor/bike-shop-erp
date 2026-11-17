"""Testes de regressao dos scripts de varredura de segredos."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GITLEAKS_IMAGE = 'ghcr.io/gitleaks/gitleaks:v8.30.1'


def _read_script(relative_path: str) -> str:
    """Retorna um script operacional para validar sua configuracao.

    Exemplo:
        source = _read_script('bin/scan-secrets')
    """
    return (PROJECT_ROOT / relative_path).read_text(encoding='utf-8')


def test_secret_scanner_scripts_pin_and_redact_gitleaks() -> None:
    """Mantem as variantes Windows e Unix alinhadas e seguras."""
    for script_path in ('bin/scan-secrets', 'bin/scan-secrets.bat'):
        source = _read_script(script_path)

        assert GITLEAKS_IMAGE in source
        assert 'docker run --rm' in source
        assert 'git --no-banner --redact --timeout 120 .' in source
