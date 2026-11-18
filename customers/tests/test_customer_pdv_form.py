"""Tests for customer validation feedback inside the point-of-sale modal."""

from django.test import RequestFactory

from customers.models import Customer
from customers.views import _pdv_customer_response, customer_create


def test_invalid_pdv_customer_submission_renders_modal_form() -> None:
    """Keep invalid quick-registration input in the modal for correction.

    Example:
        response = customer_create(request)
    """
    request = RequestFactory().post(
        '/clientes/novo/?source=pdv',
        data={'name': ''},
        HTTP_HX_REQUEST='true',
    )

    response = customer_create(request)

    assert response.status_code == 200
    assert b'id="pdv-customer-form"' in response.content
    assert b'id="id_name"' in response.content
    assert response.headers['HX-Trigger'] == 'customerFormInvalid'


def test_valid_pdv_customer_response_retargets_client_select() -> None:
    """Append a valid customer option without replacing the registration modal.

    Example:
        response = _pdv_customer_response(customer)
    """
    customer = Customer(name='Cliente de teste')

    response = _pdv_customer_response(customer)

    assert response.headers['HX-Retarget'] == '#client-select'
    assert response.headers['HX-Reswap'] == 'beforeend'
