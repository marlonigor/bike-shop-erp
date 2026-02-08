from django.db.models.signals import post_save
from django.dispatch import receiver

from core.exceptions import InsufficientStockError
from .models import StockMovement, Stock


@receiver(post_save, sender=StockMovement)
def update_stock_balance(sender, instance, created, **kwargs):
    """
    Atualiza o saldo da tabela Stock sempre que uma StockMovement é criada.
    
    - IN: Incrementa o saldo
    - OUT: Decrementa o saldo (valida disponibilidade)
    - ADJUST: Define saldo exato (incrementa ou decrementa conforme diferença)
    """
    if not created:
        # Se for apenas uma edição de registro já existente, não alteramos o saldo 
        # para evitar recálculos complexos e erros de auditoria.
        # Em um ERP real, edição de movimento é geralmente bloqueada.
        return

    # Busca ou cria o registro de saldo para aquele Produto + Depósito
    stock, _ = Stock.objects.get_or_create(
        product=instance.product,
        warehouse=instance.warehouse,
        defaults={'quantity': 0}
    )

    if instance.movement_type == StockMovement.MovementType.IN:
        stock.quantity += instance.quantity

    elif instance.movement_type == StockMovement.MovementType.OUT:
        # Validação de Estoque Negativo (Regra de Negócio Crítica)
        if stock.quantity < instance.quantity:
            raise InsufficientStockError(
                product=instance.product,
                warehouse=instance.warehouse,
                requested=instance.quantity,
                available=stock.quantity,
            )
        stock.quantity -= instance.quantity

    elif instance.movement_type == StockMovement.MovementType.ADJUST:
        # ADJUST: Usamos o campo new_quantity explícito para definir o novo saldo.
        if instance.new_quantity is not None:
            stock.quantity = instance.new_quantity
        else:
            # Fallback (opcional): se o campo estiver vazio, não alteramos o saldo.
            # Isso evita comportamentos imprevisíveis.
            pass

    stock.save()