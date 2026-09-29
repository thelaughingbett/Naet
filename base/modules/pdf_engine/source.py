from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


class PdfSource(ABC):
    """
    Base marker for anything that can be fed into a PDF generation strategy.
    A strategy declares which source types it accepts via `accepts`.
    """
    pass


@dataclass
class HtmlSource(PdfSource):
    """HTML string, for browser/CSS-based engines (Playwright, WeasyPrint, xhtml2pdf)."""
    html: str
    base_url: Optional[str] = None


@dataclass
class TemplateSource(PdfSource):
    """Django template + context — resolved to HTML by the strategy itself."""
    template_name: str
    context: dict = field(default_factory=dict)


@dataclass
class DataSource(PdfSource):
    """
    Structured data for programmatic/declarative engines that build a PDF
    from a schema rather than markup (e.g. a ReportLab strategy that maps
    known keys like 'title', 'table_rows' onto drawing calls).
    """
    data: dict


@dataclass
class BuilderSource(PdfSource):
    """
    Fully custom programmatic generation. The caller supplies a function
    that receives an engine-specific document/canvas object and draws
    directly onto it. Used for one-off layouts that don't fit a generic
    schema (e.g. a hand-drawn certificate with precise coordinates).

    builder: Callable[[Any], None] — receives the engine's native canvas/
             document object; the strategy is responsible for documenting
             what type that is.
    """
    builder: Callable[[Any], None]


@dataclass
class FileSource(PdfSource):
    """
    Existing PDF bytes to be transformed rather than generated from scratch
    — e.g. merging, watermarking, filling a form. For strategies that wrap
    tools like pypdf/pikepdf rather than rendering engines.
    """
    pdf_bytes: bytes
