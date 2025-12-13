from django.contrib import admin
from .models import Warehouse, Stock

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__sku')
    # Importante: Como regra, não devemos editar saldo diretamente, 
    # mas por enquanto deixaremos aberto para setup inicial.