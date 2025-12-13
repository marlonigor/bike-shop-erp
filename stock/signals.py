from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import StockMovement, Stock

@receiver(post_save, sender=StockMovement)
def update_stock_balance(sender, instance, created, **kwargs):
    """
    Atualiza o saldo da tabela Stock sempre que uma StockMovement é criada.
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

    # Lógica de Entrada e Saída
    if instance.movement_type == StockMovement.MovementType.IN:
        stock.quantity += instance.quantity
    
    elif instance.movement_type == StockMovement.MovementType.OUT:
        # Validação de Estoque Negativo (Regra de Negócio Crítica)
        if stock.quantity < instance.quantity:
            raise ValidationError(
                f"Saldo insuficiente para saída. Disponível: {stock.quantity}, Solicitado: {instance.quantity}"
            )
        stock.quantity -= instance.quantity
    
    # Nota: Tipos 'ADJUST' precisariam de lógica específica (ex: definir saldo exato),
    # mas por segurança, focamos em IN/OUT por enquanto.

    stock.save()