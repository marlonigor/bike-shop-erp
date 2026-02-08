from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Category, Brand


class ProductForm(forms.ModelForm):
    """Formulário para criação e edição de produtos."""
    
    class Meta:
        model = Product
        fields = ['sku', 'name', 'category', 'brand', 'cost', 'price']
        widgets = {
            'sku': forms.TextInput(attrs={
                'placeholder': 'Ex: PNEU-001',
                'class': 'form-control'
            }),
            'name': forms.TextInput(attrs={
                'placeholder': 'Nome do produto',
                'class': 'form-control'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'brand': forms.Select(attrs={
                'class': 'form-control'
            }),
            'cost': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
        }
        labels = {
            'sku': 'SKU (Código)',
            'name': 'Nome do Produto',
            'category': 'Categoria',
            'brand': 'Marca (opcional)',
            'cost': 'Preço de Custo (R$)',
            'price': 'Preço de Venda (R$)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].required = False
        self.fields['cost'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        cost = cleaned_data.get('cost')
        price = cleaned_data.get('price')
        
        if cost and price and price < cost:
            raise ValidationError({
                'price': 'O preço de venda não pode ser menor que o preço de custo.'
            })
        
        return cleaned_data
    
    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        
        # Verificar duplicidade (excluindo o próprio produto na edição)
        queryset = Product.objects.filter(sku=sku)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError('Já existe um produto com este SKU.')
        
        return sku.upper()  # Normalizar para maiúsculas
