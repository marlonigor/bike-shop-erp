from django.contrib import admin
from django.http import HttpRequest

from .models import Stock, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin[Warehouse]):
    list_display = ('name', 'location')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin[Stock]):
    list_display = ('product', 'warehouse', 'quantity')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku')
    # Importante: Como regra, não devemos editar saldo diretamente,
    # mas por enquanto deixaremos aberto para setup inicial.


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin[StockMovement]):
    list_display = (
        'created_at',
        'product',
        'warehouse',
        'movement_type',
        'quantity',
        'reference_type',
    )
    list_filter = ('movement_type', 'reference_type', 'warehouse', 'created_at')
    search_fields = ('product__name', 'product__sku', 'reason')

    # Regra de Segurança: Movimentações não devem ser editadas, apenas criadas.
    # Se errou, faz uma movimentação de ajuste inversa.
    def has_change_permission(self, request: HttpRequest, obj: StockMovement | None = None) -> bool:
        return False
