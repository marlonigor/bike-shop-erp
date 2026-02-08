"""
URL configuration for bikeshop project.
"""
from django.contrib import admin
from django.urls import path, include
from core.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('produtos/', include('catalog.urls')),
    path('pdv/', include('sales.urls')),
    path('estoque/', include('stock.urls')),
]
