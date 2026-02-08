from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('novo/', views.product_create, name='product_create'),
    path('<uuid:pk>/', views.product_detail, name='product_detail'),
    path('<uuid:pk>/editar/', views.product_edit, name='product_edit'),
    path('<uuid:pk>/excluir/', views.product_delete, name='product_delete'),
]
