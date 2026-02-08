from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Produtos
    path('', views.product_list, name='product_list'),
    path('novo/', views.product_create, name='product_create'),
    path('<uuid:pk>/', views.product_detail, name='product_detail'),
    path('<uuid:pk>/editar/', views.product_edit, name='product_edit'),
    path('<uuid:pk>/excluir/', views.product_delete, name='product_delete'),
    
    # Categorias
    path('categorias/', views.category_list, name='category_list'),
    path('categorias/nova/', views.category_create, name='category_create'),
    path('categorias/<uuid:pk>/editar/', views.category_edit, name='category_edit'),
    path('categorias/<uuid:pk>/excluir/', views.category_delete, name='category_delete'),
    
    # Marcas
    path('marcas/', views.brand_list, name='brand_list'),
    path('marcas/nova/', views.brand_create, name='brand_create'),
    path('marcas/<uuid:pk>/editar/', views.brand_edit, name='brand_edit'),
    path('marcas/<uuid:pk>/excluir/', views.brand_delete, name='brand_delete'),
]

