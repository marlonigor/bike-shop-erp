"""Comando para criar uma massa de demonstracao conectada e repetivel."""

from dataclasses import dataclass
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Brand, Category, Product
from customers.models import Customer
from sales.models import Sale
from sales.services import SalesService
from services.models import ServiceOrder
from services.services import ServiceOrderService
from stock.models import Warehouse
from stock.services import StockService

DEMO_PREFIX = '[DEMO]'
DIRECT_SALE_NOTE = f'{DEMO_PREFIX} Venda direta'
ACTIVE_ORDER_NOTE = f'{DEMO_PREFIX} OS em manutenção'
BILLED_ORDER_NOTE = f'{DEMO_PREFIX} Faturamento de OS'
STOCK_BALANCES: tuple[tuple[str, str, int], ...] = (
    ('bike', 'store', 2),
    ('tire', 'store', 12),
    ('tire', 'workshop', 4),
    ('chain', 'store', 8),
    ('chain', 'workshop', 3),
    ('pads', 'store', 20),
    ('pads', 'workshop', 6),
)


@dataclass(frozen=True)
class _ProductSpec:
    """Define um produto ficticio e seus relacionamentos de catalogo."""

    key: str
    sku: str
    name: str
    category_key: str
    brand_key: str
    price: Decimal
    cost: Decimal


DEMO_PRODUCT_SPECS: tuple[_ProductSpec, ...] = (
    _ProductSpec(
        'bike',
        'DEMO-BIKE-CITY',
        'Bicicleta City 700',
        'bikes',
        'caloi',
        Decimal('2899.00'),
        Decimal('2100.00'),
    ),
    _ProductSpec(
        'tire',
        'DEMO-TIRE-29',
        'Pneu MTB 29',
        'parts',
        'continental',
        Decimal('169.00'),
        Decimal('92.00'),
    ),
    _ProductSpec(
        'chain',
        'DEMO-CHAIN-11S',
        'Corrente 11 velocidades',
        'parts',
        'shimano',
        Decimal('249.00'),
        Decimal('150.00'),
    ),
    _ProductSpec(
        'pads',
        'DEMO-BRAKE-PADS',
        'Pastilha de freio hidraulico',
        'parts',
        'shimano',
        Decimal('89.00'),
        Decimal('44.00'),
    ),
    _ProductSpec(
        'tuneup',
        'DEMO-SVC-TUNEUP',
        'Revisao completa',
        'services',
        'caloi',
        Decimal('280.00'),
        Decimal('0.00'),
    ),
    _ProductSpec(
        'brakes',
        'DEMO-SVC-BRAKES',
        'Ajuste de freios',
        'services',
        'shimano',
        Decimal('90.00'),
        Decimal('0.00'),
    ),
)


def _find_or_create_category(name: str, category_type: str) -> Category:
    category = Category.objects.filter(name=name).first()
    if category is not None:
        return category
    return Category.objects.create(name=name, type=category_type)


def _create_categories() -> dict[str, Category]:
    return {
        'bikes': _find_or_create_category(f'{DEMO_PREFIX} Bicicletas', Category.Type.PRODUCT),
        'parts': _find_or_create_category(f'{DEMO_PREFIX} Pecas', Category.Type.PRODUCT),
        'services': _find_or_create_category(f'{DEMO_PREFIX} Servicos', Category.Type.SERVICE),
    }


def _find_or_create_brand(name: str) -> Brand:
    brand = Brand.objects.filter(name=name).first()
    if brand is not None:
        return brand
    return Brand.objects.create(name=name)


def _create_brands() -> dict[str, Brand]:
    return {
        'caloi': _find_or_create_brand(f'{DEMO_PREFIX} Caloi'),
        'shimano': _find_or_create_brand(f'{DEMO_PREFIX} Shimano'),
        'continental': _find_or_create_brand(f'{DEMO_PREFIX} Continental'),
    }


def _upsert_product(
    sku: str, name: str, category: Category, brand: Brand, price: Decimal, cost: Decimal
) -> Product:
    product, _ = Product.objects.update_or_create(
        sku=sku,
        defaults={
            'name': name,
            'category': category,
            'brand': brand,
            'price': price,
            'cost': cost,
            'active': True,
        },
    )
    return product


def _create_products(
    categories: dict[str, Category], brands: dict[str, Brand]
) -> dict[str, Product]:
    return {
        spec.key: _upsert_product(
            spec.sku,
            spec.name,
            categories[spec.category_key],
            brands[spec.brand_key],
            spec.price,
            spec.cost,
        )
        for spec in DEMO_PRODUCT_SPECS
    }


def _find_or_create_warehouse(name: str, location: str) -> Warehouse:
    warehouse = Warehouse.objects.filter(name=name).first()
    if warehouse is not None:
        return warehouse
    return Warehouse.objects.create(name=name, location=location)


def _create_warehouses() -> dict[str, Warehouse]:
    return {
        'store': _find_or_create_warehouse(f'{DEMO_PREFIX} Loja Centro', 'Centro'),
        'workshop': _find_or_create_warehouse(f'{DEMO_PREFIX} Oficina', 'Oficina'),
    }


def _find_or_create_customer(name: str, email: str, phone: str) -> Customer:
    customer = Customer.objects.filter(email=email).first()
    if customer is not None:
        return customer
    return Customer.objects.create(name=name, email=email, phone=phone, document='00000000000')


def _create_customers() -> dict[str, Customer]:
    return {
        'ana': _find_or_create_customer('Ana Demo', 'ana@example.test', '11999990001'),
        'bruno': _find_or_create_customer('Bruno Demo', 'bruno@example.test', '11999990002'),
        'carla': _find_or_create_customer('Carla Demo', 'carla@example.test', '11999990003'),
    }


def _set_stock_balance(product: Product, warehouse: Warehouse, quantity: int) -> None:
    StockService.adjust_stock(
        product=product,
        warehouse=warehouse,
        new_quantity=quantity,
        reason=f'{DEMO_PREFIX} Saldo de demonstracao',
    )


def _set_demo_stock(products: dict[str, Product], warehouses: dict[str, Warehouse]) -> None:
    for product_key, warehouse_key, quantity in STOCK_BALANCES:
        _set_stock_balance(products[product_key], warehouses[warehouse_key], quantity)


def _create_direct_sale(
    customers: dict[str, Customer], products: dict[str, Product], warehouses: dict[str, Warehouse]
) -> None:
    if Sale.objects.filter(notes=DIRECT_SALE_NOTE).exists():
        return
    SalesService.create_sale(
        customer=customers['ana'],
        warehouse=warehouses['store'],
        items_data=[
            {'product': products['tire'], 'quantity': 2, 'unit_price': products['tire'].price},
            {'product': products['brakes'], 'quantity': 1, 'unit_price': products['brakes'].price},
        ],
        notes=DIRECT_SALE_NOTE,
    )


def _create_active_order(
    customers: dict[str, Customer], products: dict[str, Product], warehouses: dict[str, Warehouse]
) -> None:
    if ServiceOrder.objects.filter(notes=ACTIVE_ORDER_NOTE).exists():
        return
    order = ServiceOrderService.create_order(
        customer=customers['bruno'],
        warehouse=warehouses['workshop'],
        bike_description='MTB 29 azul',
        client_reported_defect='Troca de pneu e revisao geral.',
        notes=ACTIVE_ORDER_NOTE,
    )
    ServiceOrderService.add_item(order, products['tire'], 1)
    ServiceOrderService.add_item(order, products['tuneup'], 1)
    ServiceOrderService.approve_order(order)
    ServiceOrderService.start_maintenance(order)


def _create_billed_order(
    customers: dict[str, Customer], products: dict[str, Product], warehouses: dict[str, Warehouse]
) -> None:
    if ServiceOrder.objects.filter(notes=BILLED_ORDER_NOTE).exists():
        return
    order = ServiceOrderService.create_order(
        customer=customers['carla'],
        warehouse=warehouses['workshop'],
        bike_description='Speed carbono preta',
        client_reported_defect='Corrente desgastada e freios desalinhados.',
        notes=BILLED_ORDER_NOTE,
    )
    ServiceOrderService.add_item(order, products['chain'], 1)
    ServiceOrderService.add_item(order, products['brakes'], 1)
    ServiceOrderService.approve_order(order)
    ServiceOrderService.start_maintenance(order)
    ServiceOrderService.complete_order(order)
    order.refresh_from_db()
    SalesService.create_sale_from_service_order(order, notes=BILLED_ORDER_NOTE)


@transaction.atomic
def _seed_demo_data() -> None:
    categories = _create_categories()
    brands = _create_brands()
    products = _create_products(categories, brands)
    warehouses = _create_warehouses()
    customers = _create_customers()
    _set_demo_stock(products, warehouses)
    _create_direct_sale(customers, products, warehouses)
    _create_active_order(customers, products, warehouses)
    _create_billed_order(customers, products, warehouses)
    _set_demo_stock(products, warehouses)


class Command(BaseCommand):
    """Popula dados ficticios para demonstrar os fluxos do Bike Shop ERP.

    Exemplo:
        python manage.py seed_demo_data
    """

    help = 'Cria uma massa ficticia de demonstracao sem apagar dados existentes.'

    def handle(self, *args: object, **options: object) -> None:
        """Cria ou atualiza a massa de demonstracao e informa a conclusao."""
        _seed_demo_data()
        self.stdout.write(self.style.SUCCESS('Massa de demonstracao pronta.'))
