from typing import Dict, List, Optional
from django.conf import settings
from django.utils.module_loading import import_string
from .base import AbstractPdfGenerationStrategy


class PdfStrategyRegistry:
    """
    Holds all registered PDF generation strategies.
    Integrators register their strategy once in AppConfig.ready().
    """

    _strategies: Dict[str, AbstractPdfGenerationStrategy] = {}

    # ---- registration -------------------------------------------------

    @classmethod
    def register(cls, strategy: AbstractPdfGenerationStrategy, *, override: bool = False):
        if not isinstance(strategy, AbstractPdfGenerationStrategy):
            raise TypeError(
                f"{strategy!r} must be an instance of AbstractPdfGenerationStrategy")
        if not strategy.name:
            raise ValueError(
                f"{strategy.__class__.__name__} must define a `name` attribute")
        if not strategy.accepts:
            raise ValueError(
                f"{strategy.__class__.__name__} must define `accepts`")
        if strategy.name in cls._strategies and not override:
            raise ValueError(
                f"A PDF strategy named '{strategy.name}' is already registered. "
                f"Pass override=True to replace it.")
        cls._strategies[strategy.name] = strategy

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._strategies.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """Mainly for tests."""
        cls._strategies.clear()

    # ---- lookup -------------------------------------------------------

    @classmethod
    def get(cls, name: Optional[str] = None) -> AbstractPdfGenerationStrategy:
        """
        name=None  -> settings.PDF_GENERATION_STRATEGY
        name='x'   -> alias from settings.PDF_STRATEGY_ALIASES, then a registered
                      name, then a dotted import path (registered on first use)
        """
        key = name or getattr(
            settings, "PDF_GENERATION_STRATEGY", "playwright")
        key = cls._resolve_alias(key)

        strategy = cls._strategies.get(key)
        if strategy:
            return strategy

        if "." in key:  # dotted path to a strategy class, lazily registered
            strategy_cls = import_string(key)
            instance = strategy_cls()
            if not instance.name:
                instance.name = key
            cls.register(instance, override=True)
            return instance

        raise LookupError(
            f"No PDF strategy registered as '{key}'. "
            f"Available: {cls.available_names()}"
        )

    @classmethod
    def _resolve_alias(cls, key: str) -> str:
        aliases = getattr(settings, "PDF_STRATEGY_ALIASES", {})
        seen = set()
        while key in aliases:
            if key in seen:
                raise ValueError(f"Circular PDF strategy alias at '{key}'")
            seen.add(key)
            key = aliases[key]
        return key

    @classmethod
    def all(cls) -> List[AbstractPdfGenerationStrategy]:
        return list(cls._strategies.values())

    @classmethod
    def available_names(cls) -> List[str]:
        return list(cls._strategies.keys())


registry = PdfStrategyRegistry()


def get_pdf_strategy(name: Optional[str] = None) -> AbstractPdfGenerationStrategy:
    """Convenience wrapper so views don't import the registry directly."""
    return registry.get(name)
