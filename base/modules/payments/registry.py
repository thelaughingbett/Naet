from typing import Dict, Type
from .backends import AbstractPaymentBackend


class PaymentBackendRegistry:
    """
    Holds all registered payment backends.
    Integrators register their backend once in AppConfig.ready().
    """

    _backends: Dict[str, AbstractPaymentBackend] = {}

    @classmethod
    def register(cls, backend: AbstractPaymentBackend):
        if not backend.method:
            raise ValueError(
                f"{backend.__class__.__name__} must define a `method` attribute")
        cls._backends[backend.method] = backend

    @classmethod
    def get(cls, method: str) -> AbstractPaymentBackend:
        backend = cls._backends.get(method)
        if not backend:
            raise LookupError(
                f"No payment backend registered for method '{method}'. "
                f"Available: {list(cls._backends.keys())}"
            )
        return backend

    @classmethod
    def all(cls) -> list[AbstractPaymentBackend]:
        return list(cls._backends.values())

    @classmethod
    def available_methods(cls):
        return list(cls._backends.keys())


registry = PaymentBackendRegistry()
