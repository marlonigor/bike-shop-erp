from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Unpack

from django import forms
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.utils.datastructures import MultiValueDict

from catalog.models import Product
from core.form_types import ModelFormArguments, set_choice_queryset
from customers.models import Customer
from stock.models import Warehouse

from .models import ServiceOrder, ServiceOrderChecklist, ServiceOrderItem


class ServiceOrderForm(forms.ModelForm[ServiceOrder]):
    """Formulario para abertura e edicao cadastral de Ordens de Servico."""

    class Meta:
        model = ServiceOrder
        fields = [
            'customer',
            'warehouse',
            'mechanic',
            'bike_description',
            'bike_serial_number',
            'client_reported_defect',
            'technical_diagnosis',
            'accessories_left',
            'estimated_delivery',
            'discount',
            'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control select2'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
            'mechanic': forms.Select(attrs={'class': 'form-control'}),
            'bike_description': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: Caloi Explorer Pro 29 Preto/Laranja',
                }
            ),
            'bike_serial_number': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Número gravado no quadro'}
            ),
            'client_reported_defect': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Descreva a queixa ou serviço solicitado pelo cliente...',
                }
            ),
            'technical_diagnosis': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Avaliação técnica inicial do mecânico...',
                }
            ),
            'accessories_left': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: Velocímetro, suporte caramanhola, luz traseira',
                }
            ),
            'estimated_delivery': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'}
            ),
            'discount': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00'}
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Observações internas da oficina...',
                }
            ),
        }

    def __init__(
        self,
        data: Mapping[str, object] | None = None,
        files: MultiValueDict[str, UploadedFile[bytes]] | None = None,
        **kwargs: Unpack[ModelFormArguments[ServiceOrder]],
    ) -> None:
        super().__init__(data, files, **kwargs)
        set_choice_queryset(
            self.fields['customer'], Customer.objects.filter(active=True).order_by('name')
        )
        set_choice_queryset(self.fields['warehouse'], Warehouse.objects.all().order_by('name'))
        set_choice_queryset(
            self.fields['mechanic'], User.objects.filter(is_active=True).order_by('first_name')
        )
        self.fields['mechanic'].required = False
        self.fields['technical_diagnosis'].required = False
        self.fields['accessories_left'].required = False
        self.fields['estimated_delivery'].required = False
        self.fields['discount'].required = False
        self.fields['notes'].required = False


class ProductModelChoiceField(forms.ModelChoiceField[Product]):
    """Campo de selecao que prefixa se o produto e peca fisica ou mao de obra."""

    def label_from_instance(self, obj: Product) -> str:
        tag = '[Serviço]' if obj.is_service else '[Peça]'
        return f'{tag} {obj.name} - R$ {obj.price:.2f}'


class ServiceOrderItemForm(forms.ModelForm[ServiceOrderItem]):
    """Formulario para adicao de pecas ou servicos a uma Ordem de Servico."""

    product = ProductModelChoiceField(
        queryset=Product.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    class Meta:
        model = ServiceOrderItem
        fields = ['product', 'quantity', 'unit_price', 'notes']
        widgets = {
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1', 'value': '1'}
            ),
            'unit_price': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Preço tabela'}
            ),
            'notes': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Observações do item'}
            ),
        }

    def __init__(
        self,
        data: Mapping[str, object] | None = None,
        files: MultiValueDict[str, UploadedFile[bytes]] | None = None,
        **kwargs: Unpack[ModelFormArguments[ServiceOrderItem]],
    ) -> None:
        super().__init__(data, files, **kwargs)
        set_choice_queryset(
            self.fields['product'],
            Product.objects.filter(active=True).order_by('is_service', 'name'),
        )
        self.fields['unit_price'].required = False
        self.fields['notes'].required = False

    def clean(self) -> dict[str, object]:
        cleaned_data: dict[str, object] = super().clean() or {}
        product = cleaned_data.get('product')
        unit_price = cleaned_data.get('unit_price')

        if isinstance(product, Product) and (unit_price is None or unit_price == Decimal('0.00')):
            cleaned_data['unit_price'] = product.price

        return cleaned_data


class ServiceOrderChecklistForm(forms.ModelForm[ServiceOrderChecklist]):
    """Formulario para inspecao tecnica e preenchimento de checklist de entrada da bike."""

    class Meta:
        model = ServiceOrderChecklist
        fields = [
            'frame_condition',
            'tires_condition',
            'brakes_condition',
            'drivetrain_condition',
            'suspension_condition',
            'has_computer',
            'has_lights',
            'has_saddlebag',
            'has_bottle_cage',
            'has_pedals',
            'observations',
        ]
        widgets = {
            'frame_condition': forms.Select(attrs={'class': 'form-control'}),
            'tires_condition': forms.Select(attrs={'class': 'form-control'}),
            'brakes_condition': forms.Select(attrs={'class': 'form-control'}),
            'drivetrain_condition': forms.Select(attrs={'class': 'form-control'}),
            'suspension_condition': forms.Select(attrs={'class': 'form-control'}),
            'observations': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Descreva arranhões ou detalhes prévios da bicicleta...',
                }
            ),
        }
