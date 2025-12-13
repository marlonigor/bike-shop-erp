from django.db import models
from core.models import ModelBase
from catalog.models import Product

class Warehouse(ModelBase):
    name = models.CharField(max_length=100, verbose_name="Nome")
    location = models.CharField(max_length=100, verbose_name="Localização")

    class Meta:
        verbose_name = "Depósito"
        verbose_name_plural = "Depósitos"
        ordering = ['name']

    def __str__(self):
        return self.name

class Stock(ModelBase):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='stocks',
        verbose_name="Produto"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='stocks',
        verbose_name="Depósito"
    )
    quantity = models.IntegerField(default=0, verbose_name="Quantidade")

    class Meta:
        verbose_name = "Estoque"
        verbose_name_plural = "Estoques"
        # Garante que não haja duplicidade de produto no mesmo depósito
        unique_together = [['product', 'warehouse']] 
        ordering = ['product__name']

    def __str__(self):
        return f"{self.product} em {self.warehouse}: {self.quantity}"