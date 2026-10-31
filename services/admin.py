from django.contrib import admin

from .models import ServiceOrder, ServiceOrderItem


class ServiceOrderItemInline(admin.TabularInline):
    model = ServiceOrderItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'total_price', 'notes')
    readonly_fields = ('total_price',)


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = (
        'short_id',
        'customer',
        'bike_description',
        'status',
        'total_amount',
        'mechanic',
        'created_at',
    )
    list_filter = ('status', 'warehouse', 'mechanic', 'created_at')
    search_fields = (
        'bike_description',
        'bike_serial_number',
        'customer__name',
        'customer__document',
    )
    readonly_fields = (
        'total_services',
        'total_parts',
        'total_amount',
        'completed_at',
        'delivered_at',
    )
    inlines = [ServiceOrderItemInline]

    @admin.display(description='OS')
    def short_id(self, obj: ServiceOrder) -> str:
        return f'OS-{str(obj.id)[:8]}'


@admin.register(ServiceOrderItem)
class ServiceOrderItemAdmin(admin.ModelAdmin):
    list_display = ('service_order', 'product', 'quantity', 'unit_price', 'total_price')
    list_filter = ('product__is_service',)
    search_fields = ('product__name', 'service_order__bike_description')
