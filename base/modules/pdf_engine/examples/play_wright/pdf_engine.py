from playwright.sync_api import sync_playwright
import logging
import time

logger = logging.getLogger(__name__)


def html_to_pdf_bytes(html_string: str, **pdf_options) -> bytes:
    """
    Launches a fresh Playwright + Chromium instance scoped entirely to
    this call, on whatever thread is currently running it. No shared
    browser object crosses threads, so Playwright's sync API (which
    pins its internal greenlet to the thread that started it) never
    gets asked to hand control to a thread it doesn't recognize.

    Slower than a shared browser (pays Chromium launch cost — roughly
    1-2s — on every call), but correct under Django's threaded/WSGI
    request handling. If this endpoint becomes high-volume, see the
    thread-local or dedicated-worker-thread alternatives below instead
    of reintroducing a cross-thread singleton.
    """
    t0 = time.perf_counter()
    with sync_playwright() as p:
        t1 = time.perf_counter()
        browser = p.chromium.launch()
        t2 = time.perf_counter()
        try:
            page = browser.new_page()
            page.set_content(html_string, wait_until="load")
            t3 = time.perf_counter()

            pdf_bytes = page.pdf(
                format=pdf_options.get("format", "A4"),
                print_background=True,
                prefer_css_page_size=True
            )
            t4 = time.perf_counter()
            logger.warning(
                f"playwright start={t1-t0:.2f}s launch={t2-t1:.2f}s "
                f"set_content={t3-t2:.2f}s pdf={t4-t3:.2f}s total={t4-t0:.2f}s"
            )
            return pdf_bytes
        finally:
            browser.close()
