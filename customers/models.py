from django.db import models

from core.models import ModelBase


class Customer(ModelBase):
    """
    Modelo de Cliente para gestao cadastral, historico e vinculo com vendas e servicos.

    Exemplo de uso:
        customer = Customer.objects.create(
            name='Carlos Santana',
            email='carlos@exemplo.com',
            phone='11987654321',
            document='12345678901',
            active=True
        )
    """

    name = models.CharField(max_length=255, verbose_name='Nome')
    email = models.EmailField(verbose_name='E-mail', blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name='Telefone', blank=True, null=True)
    document = models.CharField(
        max_length=20,
        verbose_name='CPF/CNPJ',
        blank=True,
        null=True,
        help_text='Apenas números',
    )
    active = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name
