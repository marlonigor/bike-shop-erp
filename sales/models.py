from django.db import models
from core.models import ModelBase, Client
from catalog.models import Product
from stock.models import Warehouse

class Sale(ModelBase):
    """
    Representa o cabeçalho de uma venda.
    """
    class Status(models.TextChoices):
        COMPLETED = 'COMPLETED', 'Concluída'
        CANCELLED = 'CANCELLED', 'Cancelada'

    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name="Cliente"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name="Depósito de Origem"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Valor Total"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
        verbose_name="Status"
    )
    notes = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"
        ordering = ['-created_at']

    def __str__(self):
        return f"Venda {self.id} - {self.client.name}"

class SaleItem(ModelBase):
    """
    Representa um item individual dentro de uma venda.
    """
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Venda"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name="Produto"
    )
    quantity = models.PositiveIntegerField(verbose_name="Quantidade")
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Preço Unitário"
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Preço Total"
    )

    class Meta:
        verbose_name = "Item da Venda"
        verbose_name_plural = "Itens da Venda"

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
