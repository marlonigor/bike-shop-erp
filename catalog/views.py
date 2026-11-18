import json
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib import messages
from django.db.models import IntegerField, ProtectedError, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BrandForm, CategoryForm, ProductForm
from .models import Brand, Category, Product


@dataclass(frozen=True)
class _ProductListFilters:
    """Representa os critérios ativos na listagem de produtos.

    Exemplo:
        filters = _ProductListFilters(None, '', None, None, '')
    """

    category_id: str | None
    search: str
    min_price: Decimal | None
    max_price: Decimal | None
    availability: str


def _hx_or_redirect(
    request: HttpRequest, trigger: str, redirect_to: str, message: str | None = None
) -> HttpResponse:
    """Retorna 204 com trigger para HTMX ou redireciona a navegacao padrao com mensagem."""
    if message:
        messages.success(request, message)
    if request.headers.get('HX-Request'):
        payload: dict[str, Any] = {trigger: True}
        if message:
            payload['showToast'] = {'message': message, 'type': 'success'}
        return HttpResponse(status=204, headers={'HX-Trigger': json.dumps(payload)})
    return redirect(redirect_to)


def _parse_non_negative_price(value: str | None) -> Decimal | None:
    """Converte um preço válido para Decimal sem rejeitar uma busca incompleta.

    Exemplo:
        price = _parse_non_negative_price('99.90')
    """
    if not value:
        return None
    try:
        price = Decimal(value)
    except InvalidOperation:
        return None
    return price if price.is_finite() and price >= 0 else None


def _extract_product_filters(request: HttpRequest) -> _ProductListFilters:
    """Normaliza os valores recebidos pelos controles de filtro do catálogo.

    Exemplo:
        filters = _extract_product_filters(request)
    """
    availability = request.GET.get('availability', '')
    allowed_availability = {'IN_STOCK', 'OUT_OF_STOCK'}
    return _ProductListFilters(
        category_id=request.GET.get('category'),
        search=request.GET.get('q', '').strip(),
        min_price=_parse_non_negative_price(request.GET.get('min_price')),
        max_price=_parse_non_negative_price(request.GET.get('max_price')),
        availability=availability if availability in allowed_availability else '',
    )


def _filter_products_by_price(
    products: QuerySet[Product], filters: _ProductListFilters
) -> QuerySet[Product]:
    """Restringe produtos à faixa de preço de venda preenchida pelo operador.

    Exemplo:
        products = _filter_products_by_price(products, filters)
    """
    if filters.min_price is not None:
        products = products.filter(price__gte=filters.min_price)
    if filters.max_price is not None:
        products = products.filter(price__lte=filters.max_price)
    return products


def _filter_products_by_availability(
    products: QuerySet[Product], availability: str
) -> QuerySet[Product]:
    """Filtra peças pelo saldo total e mantém serviços disponíveis sem estoque.

    Exemplo:
        products = _filter_products_by_availability(products, 'IN_STOCK')
    """
    if not availability:
        return products
    products = products.annotate(
        total_stock=Coalesce(Sum('stocks__quantity'), Value(0), output_field=IntegerField())
    )
    if availability == 'IN_STOCK':
        return products.filter(Q(is_service=True) | Q(total_stock__gt=0))
    return products.filter(is_service=False, total_stock__lte=0)


def _filter_products(
    request: HttpRequest,
) -> tuple[QuerySet[Product], list[Category], _ProductListFilters]:
    """Aplica busca, categoria, preço e disponibilidade à listagem de produtos."""
    filters = _extract_product_filters(request)
    products: QuerySet[Product] = Product.objects.select_related('category', 'brand').order_by(
        'name'
    )
    categories = list(Category.objects.all())
    if filters.category_id:
        products = products.filter(category_id=filters.category_id)
    for cat in categories:
        cat.is_selected = str(cat.id) == filters.category_id
    if filters.search:
        products = products.filter(
            Q(name__icontains=filters.search) | Q(sku__icontains=filters.search)
        )
    products = _filter_products_by_price(products, filters)
    return _filter_products_by_availability(products, filters.availability), categories, filters


def product_list(request: HttpRequest) -> HttpResponse:
    """Lista produtos ativos com suporte a filtros e renderizacao parcial HTMX."""
    products, categories, filters = _filter_products(request)
    context = {
        'products': products,
        'categories': categories,
        'selected_category': filters.category_id,
        'search': filters.search,
        'min_price': filters.min_price,
        'max_price': filters.max_price,
        'availability': filters.availability,
    }
    template = (
        'catalog/partials/product_table.html'
        if request.headers.get('HX-Request')
        else 'catalog/product_list.html'
    )
    return render(request, template, context)


def product_create(request: HttpRequest) -> HttpResponse:
    """Cria um novo produto via formulario padrao ou requisicao HTMX."""
    if request.method != 'POST':
        return render(request, 'catalog/product_form.html', {'form': ProductForm()})

    form = ProductForm(request.POST)
    if not form.is_valid():
        return render(request, 'catalog/product_form.html', {'form': form})

    product = form.save()
    msg = f"Produto '{product.name}' cadastrado com sucesso!"
    return _hx_or_redirect(request, 'productListChanged', 'catalog:product_list', message=msg)


def product_edit(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Atualiza dados cadastrais de um produto existente."""
    product = get_object_or_404(Product, pk=pk)
    if request.method != 'POST':
        form = ProductForm(instance=product)
        return render(request, 'catalog/product_form.html', {'product': product, 'form': form})

    form = ProductForm(request.POST, instance=product)
    if not form.is_valid():
        return render(request, 'catalog/product_form.html', {'product': product, 'form': form})

    product = form.save()
    msg = f"Produto '{product.name}' atualizado com sucesso!"
    return _hx_or_redirect(request, 'productListChanged', 'catalog:product_list', message=msg)


def product_delete(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Desativa logicamente um produto do catalogo."""
    product = get_object_or_404(Product, pk=pk)
    if request.method != 'POST':
        return render(request, 'catalog/product_confirm_delete.html', {'product': product})

    product.active = False
    product.save()
    msg = f"Produto '{product.name}' desativado com sucesso."
    return _hx_or_redirect(request, 'productListChanged', 'catalog:product_list', message=msg)


def _build_product_metrics(product: Product) -> dict[str, Any]:
    """Calcula indicadores financeiros e operacionais consolidados do produto."""
    from sales.models import SaleItem
    from stock.models import Stock

    margin = (
        ((product.price - product.cost) / product.price * 100)
        if product.price > 0
        else Decimal('0.00')
    )
    stock_by_wh = list(Stock.objects.filter(product=product).select_related('warehouse'))
    sales_history = list(
        SaleItem.objects.filter(product=product)
        .select_related('sale', 'sale__customer')
        .order_by('-created_at')[:10]
    )
    sales_agg = SaleItem.objects.filter(product=product).aggregate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('total_price'),
    )
    return {
        'product': product,
        'margin': margin,
        'stock_by_warehouse': stock_by_wh,
        'total_stock': sum(s.quantity for s in stock_by_wh),
        'sales_history': sales_history,
        'total_sold': sales_agg['total_sold'] or 0,
        'total_revenue': sales_agg['total_revenue'] or Decimal('0.00'),
    }


def product_detail(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Exibe indicadores consolidados e historico de movimentacao do produto."""
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), pk=pk)
    return render(request, 'catalog/product_detail.html', _build_product_metrics(product))


def category_list(request: HttpRequest) -> HttpResponse:
    """Lista todas as categorias com suporte a renderizacao parcial para HTMX."""
    context = {'categories': Category.objects.all()}
    template = (
        'catalog/partials/category_table.html'
        if request.headers.get('HX-Request')
        else 'catalog/category_list.html'
    )
    return render(request, template, context)


def category_create(request: HttpRequest) -> HttpResponse:
    """Cadastra uma nova categoria no sistema."""
    if request.method != 'POST':
        return render(request, 'catalog/category_form.html', {'form': CategoryForm()})

    form = CategoryForm(request.POST)
    if not form.is_valid():
        return render(request, 'catalog/category_form.html', {'form': form})

    category = form.save()
    msg = f"Categoria '{category.name}' cadastrada com sucesso!"
    return _hx_or_redirect(request, 'categoryListChanged', 'catalog:category_list', message=msg)


def category_edit(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Edita uma categoria existente."""
    category = get_object_or_404(Category, pk=pk)
    if request.method != 'POST':
        form = CategoryForm(instance=category)
        return render(request, 'catalog/category_form.html', {'form': form, 'category': category})

    form = CategoryForm(request.POST, instance=category)
    if not form.is_valid():
        return render(request, 'catalog/category_form.html', {'form': form, 'category': category})

    category = form.save()
    msg = f"Categoria '{category.name}' atualizada com sucesso!"
    return _hx_or_redirect(request, 'categoryListChanged', 'catalog:category_list', message=msg)


def category_delete(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Remove uma categoria do sistema."""
    category = get_object_or_404(Category, pk=pk)
    if request.method != 'POST':
        return render(request, 'catalog/category_confirm_delete.html', {'category': category})

    try:
        category.delete()
        msg = f"Categoria '{category.name}' removida com sucesso."
        return _hx_or_redirect(request, 'categoryListChanged', 'catalog:category_list', message=msg)
    except ProtectedError:
        error_msg = f"Não é possível excluir a categoria '{category.name}', pois existem produtos vinculados a ela."
        if request.headers.get('HX-Request'):
            payload = {'showToast': {'message': error_msg, 'type': 'danger'}}
            return HttpResponse(status=400, headers={'HX-Trigger': json.dumps(payload)})
        messages.error(request, error_msg)
        return redirect('catalog:category_list')


def brand_list(request: HttpRequest) -> HttpResponse:
    """Lista todas as marcas cadastradas com suporte a HTMX."""
    context = {'brands': Brand.objects.all()}
    template = (
        'catalog/partials/brand_table.html'
        if request.headers.get('HX-Request')
        else 'catalog/brand_list.html'
    )
    return render(request, template, context)


def brand_create(request: HttpRequest) -> HttpResponse:
    """Cadastra uma nova marca."""
    if request.method != 'POST':
        return render(request, 'catalog/brand_form.html', {'form': BrandForm()})

    form = BrandForm(request.POST)
    if not form.is_valid():
        return render(request, 'catalog/brand_form.html', {'form': form})

    brand = form.save()
    msg = f"Marca '{brand.name}' cadastrada com sucesso!"
    return _hx_or_redirect(request, 'brandListChanged', 'catalog:brand_list', message=msg)


def brand_edit(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Edita dados cadastrais de uma marca."""
    brand = get_object_or_404(Brand, pk=pk)
    if request.method != 'POST':
        form = BrandForm(instance=brand)
        return render(request, 'catalog/brand_form.html', {'form': form, 'brand': brand})

    form = BrandForm(request.POST, instance=brand)
    if not form.is_valid():
        return render(request, 'catalog/brand_form.html', {'form': form, 'brand': brand})

    brand = form.save()
    msg = f"Marca '{brand.name}' atualizada com sucesso!"
    return _hx_or_redirect(request, 'brandListChanged', 'catalog:brand_list', message=msg)


def brand_delete(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Remove uma marca do sistema."""
    brand = get_object_or_404(Brand, pk=pk)
    if request.method != 'POST':
        return render(request, 'catalog/brand_confirm_delete.html', {'brand': brand})

    try:
        brand.delete()
        msg = f"Marca '{brand.name}' removida com sucesso."
        return _hx_or_redirect(request, 'brandListChanged', 'catalog:brand_list', message=msg)
    except ProtectedError:
        error_msg = (
            f"Não é possível excluir a marca '{brand.name}', pois existem registros dependentes."
        )
        if request.headers.get('HX-Request'):
            payload = {'showToast': {'message': error_msg, 'type': 'danger'}}
            return HttpResponse(status=400, headers={'HX-Trigger': json.dumps(payload)})
        messages.error(request, error_msg)
        return redirect('catalog:brand_list')
