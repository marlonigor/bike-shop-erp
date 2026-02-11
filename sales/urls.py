from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.pdv, name='pdv'),
    path('buscar/', views.product_search, name='product_search'),
    path('adicionar/', views.cart_add, name='cart_add'),
    path('remover/', views.cart_remove, name='cart_remove'),
    path('atualizar/', views.cart_update, name='cart_update'),
    path('limpar/', views.cart_clear, name='cart_clear'),
    path('finalizar/', views.sale_complete, name='sale_complete'),
]
