import pytest
from stock.services.stock_service import StockService
from stock.models import Stock, Warehouse
from core.exceptions import InsufficientStockError
from catalog.models import Product, Category, Brand

@pytest.mark.django_db
class TestStockService:
    
    @pytest.fixture
    def setup_data(self):
        category = Category.objects.create(name='Bikes', type='product')
        brand = Brand.objects.create(name='Caloi')
        product = Product.objects.create(name='Bike', sku='B-01', price=100.0, cost=50.0, category=category, brand=brand)
        warehouse = Warehouse.objects.create(name='Depósito Central', location='SP')
        stock = Stock.objects.create(product=product, warehouse=warehouse, quantity=10)
        
        return {'product': product, 'warehouse': warehouse, 'stock': stock}

    def test_add_stock_increases_quantity(self, setup_data):
        StockService.add_stock(
            product=setup_data['product'],
            warehouse=setup_data['warehouse'],
            quantity=5,
            reason='Compra'
        )
        setup_data['stock'].refresh_from_db()
        # 10 inicial + 5 adicionados = 15
        assert setup_data['stock'].quantity == 15

    def test_remove_stock_decreases_quantity(self, setup_data):
        StockService.remove_stock(
            product=setup_data['product'],
            warehouse=setup_data['warehouse'],
            quantity=3,
            reason='Venda'
        )
        setup_data['stock'].refresh_from_db()
        # 10 inicial - 3 removidos = 7
        assert setup_data['stock'].quantity == 7

    def test_remove_stock_insufficient_raises_error(self, setup_data):
        with pytest.raises(InsufficientStockError):
            StockService.remove_stock(
                product=setup_data['product'],
                warehouse=setup_data['warehouse'],
                quantity=20, # Maior que 10
                reason='Venda'
            )

    def test_adjust_stock_sets_exact_quantity(self, setup_data):
        StockService.adjust_stock(
            product=setup_data['product'],
            warehouse=setup_data['warehouse'],
            new_quantity=50,
            reason='Contagem Inventário'
        )
        setup_data['stock'].refresh_from_db()
        assert setup_data['stock'].quantity == 50
