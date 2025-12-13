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