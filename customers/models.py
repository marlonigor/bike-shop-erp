from django.db import models
from core.models import ModelBase

class Customer(ModelBase):
    name = models.CharField(max_length=255, verbose_name="Nome")
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Telefone", blank=True, null=True)
    document = models.CharField(max_length=20, verbose_name="CPF/CNPJ", blank=True, null=True)
    active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['name']

    def __str__(self):
        return self.name
