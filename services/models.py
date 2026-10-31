from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from catalog.models import Product
from core.exceptions import InvalidStatusTransitionError
from core.models import ModelBase
from customers.models import Customer
from stock.models import Warehouse


class ServiceOrder(ModelBase):
    """
    Representa uma Ordem de Servico (OS) da oficina mecanica de bicicletas.
    Gerencia o ciclo de vida desde o orcamento ate a entrega final com pecas e servicos.
    """

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Orçamento'
        APPROVED = 'APPROVED', 'Aprovada'
        IN_PROGRESS = 'IN_PROGRESS', 'Em Manutenção'
        COMPLETED = 'COMPLETED', 'Concluída'
        DELIVERED = 'DELIVERED', 'Entregue'
        CANCELLED = 'CANCELLED', 'Cancelada'

    VALID_TRANSITIONS: dict[str, set[str]] = {
        'DRAFT': {'APPROVED', 'CANCELLED'},
        'APPROVED': {'IN_PROGRESS', 'CANCELLED'},
        'IN_PROGRESS': {'COMPLETED', 'CANCELLED'},
        'COMPLETED': {'DELIVERED', 'IN_PROGRESS', 'CANCELLED'},
        'DELIVERED': set(),
        'CANCELLED': set(),
    }

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='service_orders',
        verbose_name='Cliente',
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='service_orders',
        verbose_name='Depósito de Peças',
    )
    mechanic = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_orders',
        verbose_name='Mecânico Responsável',
    )
    bike_description = models.CharField(
        max_length=200,
        verbose_name='Bicicleta (Marca / Modelo / Cor)',
        help_text='Ex: Caloi Explorer Pro 29 Preta',
    )
    bike_serial_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Nº de Série / Quadro',
        help_text='Número gravado no quadro da bicicleta',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Status da OS',
    )
    client_reported_defect = models.TextField(
        verbose_name='Problema Relatado pelo Cliente',
    )
    technical_diagnosis = models.TextField(
        blank=True,
        verbose_name='Diagnóstico Técnico',
    )
    accessories_left = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Acessórios Deixados',
        help_text='Ex: Bolsa de selim, velocímetro, luz dianteira',
    )
    estimated_delivery = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Previsão de Entrega',
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Conclusão Técnica',
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data de Entrega ao Cliente',
    )
    total_services = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total de Serviços (Mão de Obra)',
    )
    total_parts = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total de Peças',
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Desconto (R$)',
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor Total da OS',
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Observações Internas',
    )

    class Meta:
        verbose_name = 'Ordem de Serviço'
        verbose_name_plural = 'Ordens de Serviço'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'OS {str(self.id)[:8]} - {self.bike_description} ({self.customer.name})'

    def can_transition_to(self, target_status: str) -> bool:
        """Verifica se o novo status e uma transicao valida a partir do status atual."""
        allowed = self.VALID_TRANSITIONS.get(self.status, set())
        return target_status in allowed

    def change_status(self, target_status: str) -> None:
        """
        Altera o status da Ordem de Servico respeitando a maquina de estados.
        Dispara InvalidStatusTransitionError se a transicao nao for permitida.
        """
        if not self.can_transition_to(target_status):
            allowed = self.VALID_TRANSITIONS.get(self.status, set())
            raise InvalidStatusTransitionError(
                model_name='ServiceOrder',
                current_status=self.status,
                target_status=target_status,
                allowed=sorted(allowed),
            )

        self.status = target_status
        now = timezone.now()
        if target_status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = now
        elif target_status == self.Status.DELIVERED and not self.delivered_at:
            self.delivered_at = now
        self.save()

    def recalculate_totals(self) -> None:
        """Recalcula subsecoes de pecas, servicos e total liquido da OS."""
        services_sum = Decimal('0.00')
        parts_sum = Decimal('0.00')

        for item in self.items.select_related('product'):
            if item.product.is_service:
                services_sum += item.total_price
            else:
                parts_sum += item.total_price

        self.total_services = services_sum
        self.total_parts = parts_sum
        gross_total = services_sum + parts_sum
        self.total_amount = max(Decimal('0.00'), gross_total - self.discount)
        self.save(update_fields=['total_services', 'total_parts', 'total_amount', 'updated_at'])


class ServiceOrderItem(ModelBase):
    """
    Item pertencente a uma Ordem de Servico.
    Pode representar tanto mao de obra (servico) quanto peca fisica aplicada.
    """

    service_order = models.ForeignKey(
        ServiceOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Ordem de Serviço',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='service_order_items',
        verbose_name='Item / Serviço',
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Quantidade',
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço Unitário (R$)',
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Preço Total (R$)',
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Observações do Item',
    )

    class Meta:
        verbose_name = 'Item da Ordem de Serviço'
        verbose_name_plural = 'Itens da Ordem de Serviço'
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.product.name} (x{self.quantity}) - OS {str(self.service_order_id)[:8]}'

    @property
    def is_service(self) -> bool:
        """Indica se o item e mao de obra ou servico imaterial."""
        return self.product.is_service

    def save(self, *args, **kwargs) -> None:
        """Garante consistencia do preco total no salvamento."""
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
