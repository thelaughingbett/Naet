from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Type
from .source import PdfSource


@dataclass
class PdfGenerationResult:
    success:   bool
    pdf_bytes: Optional[bytes] = None
    message:   str = ""
    engine:    str = ""


class AbstractPdfGenerationStrategy(ABC):
    """
    Contract every PDF generation backend must implement.

    Unlike the earlier HTML-only version, a strategy now declares which
    PdfSource type(s) it accepts via `accepts`. The caller builds whichever
    source object matches the data it has (HTML string, structured data,
    a drawing callback, etc.) and hands it to whatever strategy is registered
    — the view/service layer never needs to know which concrete engine is
    behind PDF_GENERATION_STRATEGY.

    ---
    Implementors must follow these rules:

    1. Declare `accepts` — a tuple of PdfSource subclasses this strategy
       knows how to handle.

    2. ALWAYS return a PdfGenerationResult — never raise.

    3. If given an unsupported source type, return success=False with a
       clear message (e.g. "PlaywrightPdfStrategy only accepts HtmlSource
       or TemplateSource, got DataSource") rather than raising a TypeError.

    4. NEVER touch the DB or filesystem for persistence.
    """

    name: str = ""
    accepts: tuple[Type[PdfSource], ...] = ()

    @abstractmethod
    def generate(self, source: PdfSource, **options) -> PdfGenerationResult:
        raise NotImplementedError

    def supports(self, source: PdfSource) -> bool:
        return isinstance(source, self.accepts)

    def describe(self) -> str:
        return self.__class__.__name__
