from django.template.loader import render_to_string
from ...base import AbstractPdfGenerationStrategy, PdfGenerationResult
from ...source import HtmlSource, TemplateSource, PdfSource


def _resolve_html(source: PdfSource) -> str:
    """Shared helper: HTML-based strategies accept either raw HTML or a template+context."""
    if isinstance(source, HtmlSource):
        return source.html
    if isinstance(source, TemplateSource):
        return render_to_string(source.template_name, source.context)
    raise TypeError(f"Cannot resolve HTML from {type(source).__name__}")


class PlaywrightPdfStrategy(AbstractPdfGenerationStrategy):
    name = "playwright"
    accepts = (HtmlSource, TemplateSource)

    def generate(self, source: PdfSource, **options) -> PdfGenerationResult:
        if not self.supports(source):
            return PdfGenerationResult(
                success=False, engine="playwright",
                message=f"PlaywrightPdfStrategy only accepts {self.accepts}, got {type(source).__name__}",
            )
        try:
            from base.modules.pdf_engine.examples.play_wright.pdf_engine import html_to_pdf_bytes
            html = _resolve_html(source)

            pdf_bytes = html_to_pdf_bytes(html)

            return PdfGenerationResult(success=True, pdf_bytes=pdf_bytes, engine="playwright")

        except Exception as e:
            return PdfGenerationResult(success=False, message=str(e), engine="playwright")
