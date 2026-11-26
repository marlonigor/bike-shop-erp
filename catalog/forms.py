from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Unpack

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.datastructures import MultiValueDict

from core.form_types import ModelFormArguments

from .models import Brand, Category, Product


class ProductForm(forms.ModelForm[Product]):
    """Formulário para criação e edição de produtos."""

    class Meta:
        model = Product
        fields = ['sku', 'name', 'category', 'brand', 'cost', 'price']
        widgets = {
            'sku': forms.TextInput(attrs={'placeholder': 'Ex: PNEU-001', 'class': 'form-control'}),
            'name': forms.TextInput(
                attrs={'placeholder': 'Nome do produto', 'class': 'form-control'}
            ),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(
                attrs={'placeholder': '0.00', 'class': 'form-control', 'step': '0.01', 'min': '0'}
            ),
            'price': forms.NumberInput(
                attrs={'placeholder': '0.00', 'class': 'form-control', 'step': '0.01', 'min': '0'}
            ),
        }
        labels = {
            'sku': 'SKU (Código)',
            'name': 'Nome do Produto',
            'category': 'Categoria',
            'brand': 'Marca (opcional)',
            'cost': 'Preço de Custo (R$)',
            'price': 'Preço de Venda (R$)',
        }

    def __init__(
        self,
        data: Mapping[str, object] | None = None,
        files: MultiValueDict[str, UploadedFile[bytes]] | None = None,
        **kwargs: Unpack[ModelFormArguments[Product]],
    ) -> None:
        super().__init__(data, files, **kwargs)
        self.fields['brand'].required = False
        self.fields['cost'].required = True

    def clean(self) -> dict[str, object]:
        cleaned_data: dict[str, object] = super().clean() or {}
        cost = cleaned_data.get('cost')
        price = cleaned_data.get('price')

        if (
            isinstance(cost, Decimal)
            and isinstance(price, Decimal)
            and cost
            and price
            and price < cost
        ):
            raise ValidationError(
                {'price': 'O preço de venda não pode ser menor que o preço de custo.'}
            )

        return cleaned_data

    def clean_sku(self) -> str:
        sku = self.cleaned_data.get('sku')
        if not isinstance(sku, str):
            raise ValidationError('SKU inválido: esperado texto, por exemplo PNEU-001.')

        # Verificar duplicidade (excluindo o próprio produto na edição)
        queryset = Product.objects.filter(sku=sku)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError('Já existe um produto com este SKU.')

        return sku.upper()  # Normalizar para maiúsculas


class CategoryForm(forms.ModelForm[Category]):
    """Formulário para criação e edição de categorias."""

    class Meta:
        model = Category
        fields = ['name', 'type']
        widgets = {
            'name': forms.TextInput(
                attrs={'placeholder': 'Ex: Peças de Reposição', 'class': 'form-control'}
            ),
            'type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nome da Categoria',
            'type': 'Tipo',
        }


class BrandForm(forms.ModelForm[Brand]):
    """Formulário para criação e edição de marcas."""

    class Meta:
        model = Brand
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex: Shimano', 'class': 'form-control'}),
        }
        labels = {
            'name': 'Nome da Marca',
        }
