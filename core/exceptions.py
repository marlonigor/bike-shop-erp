"""
Exceções customizadas do Bike Shop ERP.

Todas as exceções de negócio herdam de BikeShopException,
facilitando o tratamento centralizado de erros.
"""


class BikeShopException(Exception):
    """Classe base para todas as exceções do ERP."""

    pass


class InsufficientStockError(BikeShopException):
    """Lançada quando não há estoque suficiente para uma operação."""

    def __init__(self, product, warehouse, requested, available):
        self.product = product
        self.warehouse = warehouse
        self.requested = requested
        self.available = available
        message = (
            f"Estoque insuficiente para '{product}' em '{warehouse}'. "
            f"Solicitado: {requested}, Disponível: {available}"
        )
        super().__init__(message)


class InvalidStatusTransitionError(BikeShopException):
    """Lançada quando uma transição de status é inválida."""

    def __init__(self, model_name, current_status, target_status, allowed=None):
        self.model_name = model_name
        self.current_status = current_status
        self.target_status = target_status
        self.allowed = allowed
        message = (
            f"Transição inválida em {model_name}: "
            f"'{current_status}' → '{target_status}'"
        )
        if allowed:
            message += f". Transições permitidas: {allowed}"
        super().__init__(message)


class BusinessRuleViolationError(BikeShopException):
    """Lançada quando uma regra de negócio é violada."""

    def __init__(self, rule, details=None):
        self.rule = rule
        self.details = details
        message = f"Violação de regra de negócio: {rule}"
        if details:
            message += f". Detalhes: {details}"
        super().__init__(message)
