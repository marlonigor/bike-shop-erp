from django.urls import path
from . import views

app_name = 'stock'

urlpatterns = [
    path('', views.stock_list, name='stock_list'),
    path('movimentar/', views.stock_movement, name='stock_movement'),
]
