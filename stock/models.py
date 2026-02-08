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

class StockMovement(ModelBase):
    class MovementType(models.TextChoices):
        IN = 'IN', 'Entrada'
        OUT = 'OUT', 'Saída'
        ADJUST = 'ADJUST', 'Ajuste'

    class ReferenceType(models.TextChoices):
        PURCHASE = 'PURCHASE', 'Compra'
        SALE = 'SALE', 'Venda'
        SERVICE_ORDER = 'SERVICE_ORDER', 'Ordem de Serviço'
        MANUAL = 'MANUAL', 'Manual'

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name="Produto"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name="Depósito"
    )
    quantity = models.PositiveIntegerField(verbose_name="Quantidade")
    movement_type = models.CharField(
        max_length=10,
        choices=MovementType.choices,
        verbose_name="Tipo de Movimento"
    )
    reason = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="Motivo"
    )
    
    # Campos de Rastreabilidade (Generic Reference)
    reference_type = models.CharField(
        max_length=20,
        choices=ReferenceType.choices,
        default=ReferenceType.MANUAL,
        verbose_name="Origem da Movimentação"
    )
    reference_id = models.UUIDField(
        null=True, 
        blank=True, 
        verbose_name="ID da Referência"
    )
    new_quantity = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name="Nova Quantidade (Ajuste)"
    )

    class Meta:
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.sku} ({self.quantity})"