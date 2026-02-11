from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    path('', views.stock_list, name='stock_list'),
    # Novas funcionalidades
    path('ajuste-estoque/', views.stock_adjust, name='stock_adjust'),
    path('movimentar/', views.stock_movement, name='stock_movement'),
    
    path('historico/', views.stock_history, name='stock_history'),
]
