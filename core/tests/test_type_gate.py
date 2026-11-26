"""Prova que o verificador real aceita contratos válidos e rejeita violações."""

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ('source', 'expected_status', 'diagnostic'),
    [
        ('def double(value: int) -> int:\n    return value * 2\n', 0, 'Success'),
        ('def double(value):\n    return value * 2\n', 1, 'no-untyped-def'),
        ('quantity: int = "two"\n', 1, 'assignment'),
    ],
)
def test_type_gate_enforces_strict_contracts(
    tmp_path: Path, source: str, expected_status: int, diagnostic: str
) -> None:
    """As falhas são emitidas pelo mypy instalado, não por uma simulação do comando."""
    sample = tmp_path / 'type_gate_sample.py'
    sample.write_text(source)
    result = subprocess.run(
        ['mypy', '--config-file', str(PROJECT_ROOT / 'mypy.ini'), str(sample)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=45,
    )

    assert result.returncode == expected_status, result.stdout + result.stderr
    assert diagnostic in result.stdout
