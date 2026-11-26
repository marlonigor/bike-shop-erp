"""Preserva o ponto de entrada administrativo durante a adoção de tipos estritos."""

import builtins
import sys
from collections.abc import Callable, Mapping, Sequence
from types import ModuleType

import pytest

import manage

type ModuleImporter = Callable[
    [str, Mapping[str, object] | None, Mapping[str, object] | None, Sequence[str], int], ModuleType
]


class RecordedManagementCommand:
    """Registra argumentos da CLI sem executar comandos nem acessar o banco."""

    def __init__(self) -> None:
        self.arguments: list[list[str]] = []

    def __call__(self, arguments: list[str]) -> None:
        self.arguments.append(arguments.copy())


class UnavailableDjangoImporter:
    """Simula Django ausente, mantendo todos os demais imports disponíveis."""

    def __init__(self, original: ModuleImporter) -> None:
        self.original = original

    def __call__(
        self,
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == 'django.core.management':
            raise ImportError('Django indisponível no cenário de teste.')
        return self.original(name, globals, locals, fromlist, level)


def test_manage_forwards_the_command_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """O contrato de retorno não altera o encaminhamento da linha de comando."""
    command = RecordedManagementCommand()
    monkeypatch.setattr('django.core.management.execute_from_command_line', command)

    manage.main()

    assert command.arguments == [sys.argv]


def test_manage_keeps_the_installation_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """A orientação existente para Django ausente continua sendo levantada."""
    importer = UnavailableDjangoImporter(builtins.__import__)
    with monkeypatch.context() as context:
        context.setattr(builtins, '__import__', importer)
        with pytest.raises(ImportError, match="Couldn't import Django"):
            manage.main()
