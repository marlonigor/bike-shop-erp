from django import forms
from django.core.exceptions import ValidationError

from .models import Warehouse, Stock
from catalog.models import Product

class StockAdjustmentForm(forms.Form):
    """
    Formulário para ajuste manual de estoque.
    Não é um ModelForm pois a ação envolve lógica de serviço (StockService),
    não apenas salvar um modelo.
    """
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(),
        label="Depósito",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Selecione o Depósito"
    )
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.all().order_by('name'),
        label="Produto",
        widget=forms.Select(attrs={'class': 'form-control select2'}), # select2 para busca se possível
        empty_label="Selecione o Produto"
    )
    
    new_quantity = forms.IntegerField(
        label="Nova Quantidade (Saldo Real)",
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 15'
        })
    )
    
    reason = forms.CharField(
        label="Motivo do Ajuste",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Inventário mensal / Perda / Correção'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        # Aqui poderíamos validar regras complexas entre depósito e produto se necessário
        return cleaned_data
