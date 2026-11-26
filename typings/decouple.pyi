"""Contrato público de config do python-decouple 3.8, sem acesso a valores reais."""

from collections.abc import Callable
from typing import overload

class Csv:
    def __init__(
        self,
        cast: Callable[[str], str] = ...,
        delimiter: str = ...,
        strip: str | None = ...,
        post_process: Callable[[list[str]], list[str]] = ...,
    ) -> None: ...
    def __call__(self, value: str) -> list[str]: ...

@overload
def config[ValueType](
    option: str, *, cast: Callable[[str], ValueType], default: object = ...
) -> ValueType: ...
@overload
def config[ValueType](option: str, default: ValueType) -> str | ValueType: ...
@overload
def config(option: str) -> str: ...
