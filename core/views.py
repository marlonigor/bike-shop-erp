from django.shortcuts import render
from django.db.models import Sum, Count
from decimal import Decimal


def dashboard(request):
    """Dashboard principal com resumo de vendas e estoque."""
    from sales.models import Sale
    from stock.models import Stock
    from catalog.models import Product
    
    # Estatísticas
    total_vendas = Sale.objects.filter(status=Sale.Status.COMPLETED).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    vendas_hoje = Sale.objects.filter(status=Sale.Status.COMPLETED).count()
    
    produtos_ativos = Product.objects.filter(active=True).count()
    
    produtos_baixo_estoque = Stock.objects.filter(quantity__lt=5).count()
    
    # Últimas vendas
    ultimas_vendas = Sale.objects.filter(
        status=Sale.Status.COMPLETED
    ).select_related('client').order_by('-created_at')[:5]
    
    # Produtos com baixo estoque
    alertas_estoque = Stock.objects.filter(
        quantity__lt=10
    ).select_related('product', 'warehouse').order_by('quantity')[:5]
    
    context = {
        'total_vendas': total_vendas,
        'vendas_hoje': vendas_hoje,
        'produtos_ativos': produtos_ativos,
        'produtos_baixo_estoque': produtos_baixo_estoque,
        'ultimas_vendas': ultimas_vendas,
        'alertas_estoque': alertas_estoque,
    }
    
    return render(request, 'core/dashboard.html', context)
