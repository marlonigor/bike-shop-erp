"""Confere contratos usados pelos formulários tipados sem mascarar entradas inválidas."""

import pytest
from django import forms
from django.core.exceptions import ValidationError

from catalog.forms import ProductForm
from catalog.models import Product
from core.form_types import set_choice_queryset


@pytest.mark.django_db
def test_choice_queryset_preserves_the_requested_model() -> None:
    """Um campo relacional recebe o queryset tipado sem mudar suas opções."""
    field = forms.ModelChoiceField(queryset=Product.objects.none())

    set_choice_queryset(field, Product.objects.filter(active=True))

    assert field.queryset is not None
    assert field.queryset.model is Product


@pytest.mark.django_db
def test_choice_queryset_rejects_non_relational_fields() -> None:
    """Evita atribuir silenciosamente opções de modelo a um campo de texto."""
    with pytest.raises(TypeError, match='recebido: CharField; esperado ModelChoiceField'):
        set_choice_queryset(forms.CharField(), Product.objects.none())


def test_sku_cleaner_rejects_an_invalid_value() -> None:
    """O contrato do limpador exige texto, mesmo quando chamado isoladamente."""
    form = ProductForm()
    form.cleaned_data = {'sku': None}

    with pytest.raises(ValidationError, match='esperado texto'):
        form.clean_sku()
