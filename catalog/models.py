from django.db import models
from core.models import ModelBase

class Category(ModelBase):
    # Definindo as opções de tipo usando TextChoices (Boas práticas do Django modern)
    class Type(models.TextChoices):
        PRODUCT = 'PRODUCT', 'Produto'
        SERVICE = 'SERVICE', 'Serviço'

    name = models.CharField(max_length=100, verbose_name="Nome")
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.PRODUCT,
        verbose_name="Tipo"
    )

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class Brand(ModelBase):

    name = models.CharField(max_length=100, verbose_name="Nome")

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(ModelBase):
    name = models.CharField(max_length=120, verbose_name="Nome")
    sku = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="SKU (Código)"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='products',
        verbose_name="Categoria"
    )
    brand = models.ForeignKey(
        Brand, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='products',
        verbose_name="Marca"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Preço de Venda"
    )
    cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name="Preço de Custo"
    )
    is_service = models.BooleanField(
        default=False, 
        verbose_name="É serviço?"
    )
    active = models.BooleanField(
        default=True, 
        verbose_name="Ativo"
    )

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['name']

    def __str__(self):
        return f"{self.sku} - {self.name}"

    def save(self, *args, **kwargs):
        # Automatização: Se a categoria for SERVIÇO, marca o produto como serviço automaticamente
        if self.category and self.category.type == Category.Type.SERVICE:
            self.is_service = True
        else:
            self.is_service = False
        super().save(*args, **kwargs)