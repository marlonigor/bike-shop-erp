from django.contrib import admin
from .models import Category, Brand, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'created_at')
    search_fields = ('name',)
    list_filter = ('type',)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'brand', 'price', 'is_service', 'active')
    list_filter = ('category', 'brand', 'active', 'is_service')
    search_fields = ('name', 'sku')
    list_editable = ('price', 'active') # Permite editar preço direto na lista!
    autocomplete_fields = ['category', 'brand'] # Útil quando tivermos muitas marcas