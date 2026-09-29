from playwright.sync_api import sync_playwright


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
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html_string, wait_until="networkidle")
            return page.pdf(
                format=pdf_options.get("format", "A4"),
                print_background=True,
                # respects your @page { size; margin; } rule
                prefer_css_page_size=True,
            )
        finally:
            browser.close()
