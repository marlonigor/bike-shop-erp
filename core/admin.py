from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin[Supplier]):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email')
