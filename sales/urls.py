from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.pdv, name='pdv'),
    path('buscar/', views.product_search, name='product_search'),
    path('adicionar/', views.cart_add, name='cart_add'),
    path('finalizar/', views.sale_complete, name='sale_complete'),
]
