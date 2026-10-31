from django.urls import path

from . import views

app_name = 'services'

urlpatterns = [
    path('', views.service_order_list, name='service_order_list'),
    path('nova/', views.service_order_create, name='service_order_create'),
    path('<uuid:pk>/', views.service_order_detail, name='service_order_detail'),
    path('<uuid:pk>/itens/adicionar/', views.service_order_add_item, name='service_order_add_item'),
    path(
        '<uuid:pk>/itens/<uuid:item_id>/remover/',
        views.service_order_remove_item,
        name='service_order_remove_item',
    ),
    path(
        '<uuid:pk>/status/<str:target_status>/',
        views.service_order_change_status,
        name='service_order_change_status',
    ),
]
