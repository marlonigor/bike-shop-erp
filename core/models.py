import uuid
from django.db import models

class ModelBase(models.Model):
    """
    Classe base abstrata para todos os modelos do sistema.
    Adiciona ID (UUID) e timestamps automáticos.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )

    class Meta:
        abstract = True  # O Django não criará uma tabela para esta classe
        ordering = ['-created_at']

class Client(ModelBase):
    name = models.CharField(max_length=150, verbose_name="Nome Completo")
    email = models.EmailField(
        unique=True, 
        null=True, 
        blank=True, 
        verbose_name="E-mail"
    )
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Telefone"
    )
    document = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="CPF/CNPJ",
        help_text="Apenas números"
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['name']

    def __str__(self):
        return self.name

class Supplier(ModelBase):
    name = models.CharField(max_length=150, verbose_name="Razão Social/Nome")
    email = models.EmailField(
        null=True, 
        blank=True, 
        verbose_name="E-mail"
    )
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Telefone"
    )

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ['name']

    def __str__(self):
        return self.name