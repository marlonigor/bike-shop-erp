from decimal import Decimal

import pytest
from django.urls import reverse

from catalog.models import Category, Product
from services.models import ServiceOrder, ServiceOrderItem


@pytest.fixture
def service_order(db, customer, warehouse):
    return ServiceOrder.objects.create(
        customer=customer,
        warehouse=warehouse,
        bike_description='Cannondale Scalpel 29',
        client_reported_defect='Revisão de suspensão e freio',
    )


@pytest.fixture
def labor_product(db):
    cat = Category.objects.create(name='Mão de Obra', type=Category.Type.SERVICE)
    return Product.objects.create(
        name='Revisão Suspensão',
        sku='REV-SUSP',
        category=cat,
        cost=Decimal('0.00'),
        price=Decimal('200.00'),
        is_service=True,
    )


@pytest.mark.django_db
class TestServiceOrderViews:
    def test_service_order_list_view_returns_200(self, client, service_order):
        url = reverse('services:service_order_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'orders' in response.context
        assert service_order in response.context['orders']
        assert 'services/service_order_list.html' in [t.name for t in response.templates]

    def test_service_order_list_filter_by_status(self, client, service_order, customer, warehouse):
        approved_order = ServiceOrder.objects.create(
            customer=customer,
            warehouse=warehouse,
            bike_description='Bike Aprovada',
            client_reported_defect='Revisão',
            status=ServiceOrder.Status.APPROVED,
        )

        url = reverse('services:service_order_list')
        response = client.get(f'{url}?status=APPROVED')
        assert response.status_code == 200
        assert approved_order in response.context['orders']
        assert service_order not in response.context['orders']

    def test_service_order_list_htmx_returns_partial(self, client, service_order):
        url = reverse('services:service_order_list')
        response = client.get(url, headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert 'services/partials/order_table.html' in [t.name for t in response.templates]

    def test_service_order_create_view_get(self, client):
        url = reverse('services:service_order_create')
        response = client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context
        assert 'services/service_order_form.html' in [t.name for t in response.templates]

    def test_service_order_create_view_post_valid(self, client, customer, warehouse):
        url = reverse('services:service_order_create')
        data = {
            'customer': str(customer.id),
            'warehouse': str(warehouse.id),
            'bike_description': 'Soul SL329 Cinza',
            'client_reported_defect': 'Corrente quebrando',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert ServiceOrder.objects.filter(bike_description='Soul SL329 Cinza').exists()

    def test_service_order_detail_view_returns_200(self, client, service_order):
        url = reverse('services:service_order_detail', args=[service_order.id])
        response = client.get(url)
        assert response.status_code == 200
        assert response.context['order'] == service_order
        assert 'services/service_order_detail.html' in [t.name for t in response.templates]

    def test_service_order_add_item_htmx(self, client, service_order, labor_product):
        url = reverse('services:service_order_add_item', args=[service_order.id])
        data = {
            'product': str(labor_product.id),
            'quantity': 1,
            'unit_price': '200.00',
        }
        response = client.post(url, data, headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert 'showToast' in response.headers['HX-Trigger']
        assert 'services/partials/order_items_table.html' in [t.name for t in response.templates]
        assert service_order.items.count() == 1

    def test_service_order_remove_item_htmx(self, client, service_order, labor_product):
        item = ServiceOrderItem.objects.create(
            service_order=service_order,
            product=labor_product,
            quantity=1,
            unit_price=Decimal('200.00'),
        )
        url = reverse('services:service_order_remove_item', args=[service_order.id, item.id])
        response = client.post(url, headers={'HX-Request': 'true'})
        assert response.status_code == 200
        assert 'showToast' in response.headers['HX-Trigger']
        assert service_order.items.count() == 0

    def test_service_order_change_status_view(self, client, service_order):
        url = reverse(
            'services:service_order_change_status',
            args=[service_order.id, ServiceOrder.Status.APPROVED],
        )
        response = client.post(url)
        assert response.status_code == 302
        service_order.refresh_from_db()
        assert service_order.status == ServiceOrder.Status.APPROVED

    def test_service_order_item_form_product_label_distinguishes_service_and_part(
        self, labor_product
    ):
        from services.forms import ServiceOrderItemForm

        form = ServiceOrderItemForm()
        label = form.fields['product'].label_from_instance(labor_product)
        assert '[Serviço]' in label
        assert 'Revisão Suspensão' in label

    def test_service_order_invoice_view_post_success(self, client, service_order):
        service_order.status = ServiceOrder.Status.COMPLETED
        service_order.save()

        url = reverse('services:service_order_invoice', args=[service_order.id])
        response = client.post(url)
        assert response.status_code == 302
        assert response.url == reverse('services:service_order_receipt', args=[service_order.id])
        service_order.refresh_from_db()
        assert service_order.status == ServiceOrder.Status.DELIVERED
        assert service_order.sale is not None

    def test_service_order_receipt_view_returns_200(self, client, service_order):
        url = reverse('services:service_order_receipt', args=[service_order.id])
        response = client.get(url)
        assert response.status_code == 200
        assert 'services/service_order_receipt.html' in [t.name for t in response.templates]
        assert 'order' in response.context

    def test_service_order_checklist_update_view(self, client, service_order):
        url = reverse('services:service_order_checklist_update', args=[service_order.id])
        data = {
            'frame_condition': 'ATTENTION',
            'tires_condition': 'OK',
            'brakes_condition': 'DAMAGED',
            'drivetrain_condition': 'OK',
            'suspension_condition': 'NA',
            'has_computer': True,
            'has_pedals': True,
            'observations': 'Arranhão no quadro',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert response.url == reverse('services:service_order_detail', args=[service_order.id])
        service_order.refresh_from_db()
        assert service_order.checklist.frame_condition == 'ATTENTION'
        assert service_order.checklist.has_computer is True
