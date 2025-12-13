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