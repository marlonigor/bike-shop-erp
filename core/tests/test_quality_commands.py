"""Confere a ordem e a interrupção dos portões de qualidade sem Docker real."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FAKE_DOCKER = """#!/bin/sh
printf '%s\\n' "$*" >> "$DOCKER_CALL_LOG"
if [ -n "$DOCKER_FAIL_MATCH" ]; then
  case "$*" in *"$DOCKER_FAIL_MATCH"*) exit 7 ;; esac
fi
if [ "$DOCKER_REQUIRE_RAW_PATHS" = "1" ] && [ "$1" = "run" ] && [ "$MSYS_NO_PATHCONV" != "1" ]; then
  exit 9
fi
exit 0
"""


@dataclass(frozen=True)
class FakeDockerExecutable:
    """Simula saídas do Docker; exemplo: falhar ao executar mypy sem iniciar serviços."""

    directory: Path
    log: Path

    def run(
        self, script: str, fail_match: str = '', require_raw_paths: bool = False
    ) -> subprocess.CompletedProcess[str]:
        """Executa um script real com a dependência externa simulada no PATH."""
        environment = os.environ | {
            'PATH': f'{self.directory}{os.pathsep}{os.environ["PATH"]}',
            'DOCKER_CALL_LOG': str(self.log),
            'DOCKER_FAIL_MATCH': fail_match,
            'DOCKER_REQUIRE_RAW_PATHS': '1' if require_raw_paths else '0',
        }
        return subprocess.run(
            ['bash', str(PROJECT_ROOT / script)],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def calls(self) -> list[str]:
        """Retorna somente argumentos da CLI, sem valores do ambiente."""
        return self.log.read_text().splitlines()


@pytest.fixture
def fake_docker(tmp_path: Path) -> FakeDockerExecutable:
    """Cria um executável isolado para testar scripts sem rede ou banco."""
    executable = tmp_path / 'docker'
    executable.write_text(FAKE_DOCKER)
    executable.chmod(0o755)
    return FakeDockerExecutable(tmp_path, tmp_path / 'docker-calls.log')


def test_check_runs_build_types_lint_and_tests(fake_docker: FakeDockerExecutable) -> None:
    """O comando único só passa quando todas as etapas passam em ordem."""
    result = fake_docker.run('bin/check')

    assert result.returncode == 0, result.stderr
    calls = fake_docker.calls()
    assert calls.index('compose build web') < calls.index('compose run --rm web mypy')
    assert 'compose run --rm web ruff check .' in calls
    assert 'compose run --rm web ruff format --check .' in calls
    assert 'compose run --rm web python manage.py check' in calls
    assert calls[-1] == 'compose run --rm web pytest'


@pytest.mark.parametrize(
    'failed_phase', ['build web', 'mypy', 'ruff check', 'ruff format', 'manage.py check']
)
def test_check_stops_before_tests_after_a_failure(
    fake_docker: FakeDockerExecutable, failed_phase: str
) -> None:
    """Uma falha intermediária impede que commit ou CI obtenham sucesso falso."""
    result = fake_docker.run('bin/check', failed_phase)

    assert result.returncode == 7
    assert not any(call.endswith(' pytest') for call in fake_docker.calls())


@pytest.mark.parametrize('hook', ['pre-commit', 'pre-push'])
def test_hooks_propagate_a_failed_check(fake_docker: FakeDockerExecutable, hook: str) -> None:
    """Os hooks bloqueiam a ação do Git quando o verificador de tipos falha."""
    result = fake_docker.run(f'.githooks/{hook}', 'mypy')

    assert result.returncode == 7
    assert not any('pull ghcr.io/gitleaks' in call for call in fake_docker.calls())


def test_pre_push_scans_secrets_only_after_checks_pass(fake_docker: FakeDockerExecutable) -> None:
    """O push só chega à varredura após o comando completo terminar sem falhas."""
    result = fake_docker.run('.githooks/pre-push')

    assert result.returncode == 0, result.stderr
    calls = fake_docker.calls()
    scan = 'pull ghcr.io/gitleaks/gitleaks:v8.30.1'
    assert calls.index('compose run --rm web pytest') < calls.index(scan)
    assert 'git --no-banner --redact --timeout 120 .' in calls[-1]


def test_pre_push_blocks_a_failed_secret_scan(fake_docker: FakeDockerExecutable) -> None:
    """Uma falha do scanner também bloqueia a publicação, mesmo com testes aprovados."""
    result = fake_docker.run('.githooks/pre-push', 'git --no-banner')

    assert result.returncode == 7


def test_secret_scan_preserves_container_paths_under_git_bash(
    fake_docker: FakeDockerExecutable,
) -> None:
    """O Git Bash não pode converter /repo para C:/Program Files/Git/repo."""
    converter = fake_docker.directory / 'cygpath'
    converter.write_text('#!/bin/sh\nprintf "C:/quality-test-repo\\n"\n')
    converter.chmod(0o755)
    result = fake_docker.run('bin/scan-secrets', require_raw_paths=True)

    assert result.returncode == 0, result.stderr
    assert '--volume C:/quality-test-repo:/repo:ro --workdir /repo' in fake_docker.calls()[-1]
