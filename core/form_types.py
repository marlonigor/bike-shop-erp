"""Contratos dos formulários Django; exemplo: ModelFormArguments[Product]."""

from collections.abc import MutableMapping
from typing import TypedDict

from django import forms
from django.db.models import Model, QuerySet
from django.forms.renderers import BaseRenderer
from django.forms.utils import ErrorList


class ModelFormArguments[FormModel: Model](TypedDict, total=False):
    """Opções opcionais aceitas por ModelForm, preservando o modelo da instância."""

    auto_id: bool | str
    prefix: str | None
    initial: MutableMapping[str, object] | None
    error_class: type[ErrorList]
    label_suffix: str | None
    empty_permitted: bool
    instance: FormModel | None
    use_required_attribute: bool | None
    renderer: BaseRenderer | None


def set_choice_queryset(field: forms.Field, queryset: QuerySet[Model]) -> None:
    """Configura opções de um campo relacional; exemplo: limitar clientes ativos."""
    if not isinstance(field, forms.ModelChoiceField):
        raise TypeError(f'Campo recebido: {type(field).__name__}; esperado ModelChoiceField.')
    field.queryset = queryset
