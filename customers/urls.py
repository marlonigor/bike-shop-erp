from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('novo/', views.customer_create, name='customer_create'),
    path('<uuid:pk>/editar/', views.customer_edit, name='customer_edit'),
    path('<uuid:pk>/excluir/', views.customer_delete, name='customer_delete'),
]
