from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Customer
from .forms import CustomerForm

def customer_list(request):
    customers = Customer.objects.all()
    search = request.GET.get('q', '')
    if search:
        customers = customers.filter(name__icontains=search)
    
    context = {
        'customers': customers,
        'search': search
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'customers/partials/customer_table.html', context)
        
    return render(request, 'customers/customer_list.html', context)

def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('customers:customer_list')
    else:
        form = CustomerForm()
    return render(request, 'customers/customer_form.html', {'form': form})

def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('customers:customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'customers/customer_form.html', {'form': form, 'customer': customer})

def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.delete()
        return redirect('customers:customer_list')
    return redirect('customers:customer_list')
