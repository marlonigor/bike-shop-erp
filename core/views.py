from django.shortcuts import render
from django.db.models import Sum, Count, functions
from django.utils import timezone
from datetime import timedelta
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
    
    # Alertas de estoque
    alertas_estoque = Stock.objects.filter(
        quantity__lt=10
    ).select_related('product', 'warehouse').order_by('quantity')[:5]
    
    # Dados para o gráfico (últimos 6 meses)
    seis_meses_atras = timezone.now().replace(day=1) - timedelta(days=150)
    vendas_mensais = Sale.objects.filter(
        status=Sale.Status.COMPLETED,
        created_at__gte=seis_meses_atras
    ).annotate(
        month=functions.TruncMonth('created_at')
    ).values('month').annotate(
        total=Sum('total_amount')
    ).order_by('month')

    chart_labels = [v['month'].strftime('%b/%Y') for v in vendas_mensais]
    chart_data = [float(v['total']) for v in vendas_mensais]
    
    context = {
        'total_vendas': total_vendas,
        'vendas_hoje': vendas_hoje,
        'produtos_ativos': produtos_ativos,
        'produtos_baixo_estoque': produtos_baixo_estoque,
        'ultimas_vendas': ultimas_vendas,
        'alertas_estoque': alertas_estoque,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
    }
    
    return render(request, 'core/dashboard.html', context)
