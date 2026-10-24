"""Controladores web para gestao cadastral de clientes."""

import json

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomerForm
from .models import Customer


def customer_list(request: HttpRequest) -> HttpResponse:
    """Lista todos os clientes com busca por nome e suporte a HTMX."""
    customers = Customer.objects.all()
    search = request.GET.get('q', '')
    if search:
        customers = customers.filter(name__icontains=search)

    context = {'customers': customers, 'search': search}
    template = (
        'customers/partials/customer_table.html'
        if request.headers.get('HX-Request')
        else 'customers/customer_list.html'
    )
    return render(request, template, context)


def _pdv_customer_response(customer: Customer) -> HttpResponse:
    """Gera tag option selecionada e triggers HTMX para insercao imediata no PDV."""
    payload = {
        'customerCreated': {'id': str(customer.id), 'name': customer.name},
        'showToast': {'message': f'Cliente {customer.name} cadastrado com sucesso!'},
    }
    return HttpResponse(
        f'<option value="{customer.id}" selected>{customer.name}</option>',
        headers={'HX-Trigger': json.dumps(payload)},
    )


def customer_create(request: HttpRequest) -> HttpResponse:
    """Cadastra um novo cliente com suporte a inclusao rapida via PDV."""
    if request.method != 'POST':
        return render(request, 'customers/customer_form.html', {'form': CustomerForm()})

    form = CustomerForm(request.POST)
    if not form.is_valid():
        return render(request, 'customers/customer_form.html', {'form': form})

    customer = form.save()
    if not request.headers.get('HX-Request'):
        return redirect('customers:customer_list')

    if request.GET.get('source') == 'pdv':
        return _pdv_customer_response(customer)

    return HttpResponse(status=204, headers={'HX-Trigger': 'customerListChanged'})


def customer_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edita dados cadastrais de um cliente."""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method != 'POST':
        form = CustomerForm(instance=customer)
        return render(request, 'customers/customer_form.html', {'form': form, 'customer': customer})

    form = CustomerForm(request.POST, instance=customer)
    if not form.is_valid():
        return render(request, 'customers/customer_form.html', {'form': form, 'customer': customer})

    form.save()
    if request.headers.get('HX-Request'):
        return HttpResponse(status=204, headers={'HX-Trigger': 'customerListChanged'})
    return redirect('customers:customer_list')


def customer_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove ou desativa um cliente do sistema."""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method != 'POST':
        return redirect('customers:customer_list')

    customer.delete()
    if request.headers.get('HX-Request'):
        return HttpResponse(status=204, headers={'HX-Trigger': 'customerListChanged'})
    return redirect('customers:customer_list')
