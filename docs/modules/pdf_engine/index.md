# 📄 PDF Engine Module

> Everything about how documents become PDFs in Naet: how strategies work,
> how to add a new rendering engine, and how the system stays clean no matter
> which library actually draws the pages.
> Think of this as the contract between the document world and the rendering world.

---

## 🗺️ Overview

PDF generation is **pluggable by design**. Naet doesn't care whether a PDF is
rendered by headless Chromium, WeasyPrint, ReportLab, or an engine that doesn't
exist yet. Every engine is just an implementation of the same contract.

```
View / service needs a PDF
      ↓
Builds a Source object (HtmlSource, TemplateSource, DataSource, ...)
      ↓
get_pdf_strategy("transcript") looks up the strategy from the registry
      ↓
strategy.generate(source) → PdfGenerationResult
      ↓
Caller checks result.success
      ↓
Caller checksums, signs, stores, or returns the bytes
```

The view knows nothing about Playwright.
The Playwright strategy knows nothing about transcripts, signing, or the DB.
The **use case name** (`"transcript"`, `"invoice"`) is the only thing the view
knows, and settings decide which engine sits behind it.

---

## 🏗️ Architecture

```
pdfEngine/
├── base.py            # the contract: AbstractPdfGenerationStrategy, PdfGenerationResult
├── source.py          # input types: HtmlSource, TemplateSource, DataSource, ...
├── registry.py        # PdfStrategyRegistry singleton + get_pdf_strategy()
└── examples/
    ├── playwight.py   # reference strategy: HTML → PDF via headless Chromium
    └── pdf_engine     # shared engine lifecycle (Playwright browser singleton)
```

| File          | Responsibility                                                           |
| ------------- | ------------------------------------------------------------------------ |
| `base.py`     | Defines what a strategy _is_ and what it returns                         |
| `source.py`   | Defines what a strategy can be _given_                                   |
| `registry.py` | Holds registered strategies, resolves aliases, falls back to the default |
| `examples/`   | Working reference implementations. Copy one to start your own            |

---

## 📐 The Contract

Every strategy must implement **one method** and declare **two attributes**.

```python
class AbstractPdfGenerationStrategy(ABC):

    name: str = ""                              # registry key, e.g. "playwright"
    accepts: tuple[Type[PdfSource], ...] = ()   # which Source types it can consume

    @abstractmethod
    def generate(self, source: PdfSource, **options) -> PdfGenerationResult:
        """Turn a source into PDF bytes. Touch nothing in the DB or filesystem."""
        raise NotImplementedError

    def supports(self, source: PdfSource) -> bool:
        return isinstance(source, self.accepts)

    def describe(self) -> str:
        return self.__class__.__name__
```

### 📦 The result dataclass

```python
@dataclass
class PdfGenerationResult:
    success:   bool
    pdf_bytes: Optional[bytes] = None
    message:   str = ""
    engine:    str = ""    # which engine actually produced the PDF
```

| Field       | Meaning                                                                            |
| ----------- | ---------------------------------------------------------------------------------- |
| `success`   | `False` means generation failed and the caller decides what to do                  |
| `pdf_bytes` | The finished PDF. `None` when `success=False`                                      |
| `message`   | Human-readable outcome or error                                                    |
| `engine`    | Name of the engine that produced the file (useful if a strategy falls back inside) |

---

## 🧩 Source types

The input is polymorphic. A strategy declares which source types it accepts via
`accepts`, and the caller builds whichever one fits the data it has.

| Source           | Contains                                       | Used by                                        |
| ---------------- | ---------------------------------------------- | ---------------------------------------------- |
| `HtmlSource`     | A rendered HTML string (+ optional `base_url`) | Playwright, WeasyPrint, xhtml2pdf              |
| `TemplateSource` | Django template name + context                 | Same as above; resolved to HTML by strategy    |
| `DataSource`     | A structured dict (title, sections, rows)      | Schema-driven programmatic engines (ReportLab) |
| `BuilderSource`  | A callback that draws onto the engine's canvas | One-off precise layouts (certificates)         |
| `FileSource`     | Existing PDF bytes                             | Transform engines (merge, watermark, fill)     |

`BuilderSource` is the escape hatch. For an engine the abstraction doesn't
anticipate, hand the caller the native canvas and get out of the way.

---

## 🔌 Built-in strategies

| Key                 | Class                      | Accepts                        | Best for                         |
| ------------------- | -------------------------- | ------------------------------ | -------------------------------- |
| `playwright`        | `PlaywrightPdfStrategy`    | `HtmlSource`, `TemplateSource` | Rich CSS, transcripts, reports   |
| `weasyprint`        | `WeasyPrintPdfStrategy`    | `HtmlSource`, `TemplateSource` | Lightweight, Linux/Docker        |
| `xhtml2pdf`         | `Xhtml2PdfStrategy`        | `HtmlSource`, `TemplateSource` | Zero native deps, simple layouts |
| `reportlab`         | `ReportLabDataStrategy`    | `DataSource`                   | Invoices, tabular documents      |
| `reportlab-builder` | `ReportLabBuilderStrategy` | `BuilderSource`                | Certificates, exact coordinates  |

All engine imports happen lazily inside `generate()`, so registering every
strategy does **not** require every engine to be installed.

---

## ⚙️ Configuration

```python
# settings.py

# Used when the caller doesn't ask for a specific strategy
PDF_GENERATION_STRATEGY = "playwright"

# Optional: map use-case names to strategies
PDF_STRATEGY_ALIASES = {
    "transcript":  "playwright",
    "invoice":     "reportlab",
    "certificate": "reportlab-builder",
    # "receipt":   "myapp.pdf.MyCustomPdfStrategy",   # dotted paths work too
}
```

### Resolution order

`get_pdf_strategy(name)` resolves in this order:

1. `name=None` → `settings.PDF_GENERATION_STRATEGY`
2. Alias lookup in `PDF_STRATEGY_ALIASES` (chains are followed, cycles raise)
3. A strategy registered under that `name`
4. A dotted import path (imported and registered on first use)
5. Otherwise `LookupError` listing the available names

---

## 🧭 Using it in a view or service

```python
from base.modules.pdfEngine.registry import get_pdf_strategy
from base.modules.pdfEngine.source import TemplateSource, DataSource

# transcripts: HTML-rendered
result = get_pdf_strategy("transcript").generate(
    TemplateSource("transcripts/transcript_pdf.html", {"student": student})
)

# invoices: programmatic
result = get_pdf_strategy("invoice").generate(
    DataSource(data={
        "title": f"Invoice #{invoice.id}",
        "sections": [{"heading": "Items", "rows": [["Item", "Amount"], *rows]}],
    })
)

# no name: falls back to PDF_GENERATION_STRATEGY
result = get_pdf_strategy().generate(some_source)

if not result.success:
    raise RuntimeError(f"PDF failed ({result.engine}): {result.message}")

pdf_bytes = result.pdf_bytes
```

The engine only produces bytes. Everything after that (checksum, digital
signature, storage, HTTP response) belongs to the calling service:

```python
checksum   = hashlib.sha256(result.pdf_bytes).hexdigest()
signed_pdf = sign_transcript(result.pdf_bytes, student.student_id)   # pyHanko
```

---

## 🛠️ Adding a New Strategy

### Step 1: Create your strategy file

Building for your own institution:

```
pdfEngine/your_engine.py
```

Starting from a reference: copy `examples/playwight.py`.

### Step 2: Implement the contract

```python
from base.modules.pdfEngine.base import (
    AbstractPdfGenerationStrategy,
    PdfGenerationResult,
)
from base.modules.pdfEngine.source import HtmlSource, TemplateSource


class MyEnginePdfStrategy(AbstractPdfGenerationStrategy):

    name = "myengine"                       # registry key
    accepts = (HtmlSource, TemplateSource)  # what you can consume

    def generate(self, source, **options) -> PdfGenerationResult:
        if not self.supports(source):
            return PdfGenerationResult(
                success=False,
                engine=self.name,
                message=f"{self.__class__.__name__} only accepts {self.accepts}, "
                        f"got {type(source).__name__}",
            )
        try:
            import my_engine   # import lazily so the engine stays optional
            pdf_bytes = my_engine.render(source.html)
            return PdfGenerationResult(success=True, pdf_bytes=pdf_bytes, engine=self.name)
        except Exception as e:
            return PdfGenerationResult(success=False, message=str(e), engine=self.name)

    def describe(self) -> str:
        return "Renders HTML via MyEngine."
```

### Step 3: Register it

```python
# base/apps.py
class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        from base.modules.pdfEngine.registry import registry
        from base.modules.pdfEngine.your_engine import MyEnginePdfStrategy

        registry.register(MyEnginePdfStrategy())
```

### Step 4: Point a use case at it

```python
PDF_STRATEGY_ALIASES = {"transcript": "myengine"}
```

No view changes. That's the whole point.

---

## 🎭 Reference implementation: Playwright

`examples/playwight.py` is the reference strategy: HTML in, PDF out via headless
Chromium. The shared browser is deliberately kept out of the strategy class, in
`examples/pdf_engine`, so the strategy stays stateless.

```python
# examples/pdf_engine: shared browser lifecycle
import threading
from playwright.sync_api import sync_playwright

_lock = threading.Lock()
_playwright = None
_browser = None

def get_browser():
    global _playwright, _browser
    with _lock:
        if _browser is None:
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch()
        return _browser

def shutdown_browser():
    global _playwright, _browser
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _browser = _playwright = None
```

### Deploying Playwright (Render)

```bash
# build.sh
pip install -r requirements.txt
playwright install --with-deps chromium
python manage.py collectstatic --no-input
python manage.py migrate
```

If `--with-deps` fails on permissions, switch to a Docker deploy using
`mcr.microsoft.com/playwright/python:<version>-jammy`, which ships Chromium and
its system libraries preinstalled. Keep the image tag in step with your pinned
`playwright` version.

### ⚠️ Threading

`ready()` runs once **per process**. Under gunicorn each worker gets its own
browser, which is fine. Within a worker, the sync Playwright browser is **not
thread-safe**. With `--threads` / `gthread` workers, serialize page creation with
a lock or use a small pool of browsers. For batch runs (semester-end transcripts),
prefer a background worker (Celery) so Chromium stays out of the web process.

---

## 🚦 The Golden Rules

> These keep engines swappable. Breaking them couples your view logic to one library.

**1. Never touch the DB or filesystem inside `generate()`**
A strategy converts a source into bytes. Saving, checksumming and signing are the
caller's job.

**2. Always return a `PdfGenerationResult`. Never raise from `generate()`**
Catch exceptions internally and return `success=False` with a message.
_Configuration errors are the exception:_ an unknown strategy name raises
`LookupError` from the registry, because it is a setup mistake, not a generation
failure.

**3. Declare `name` and `accepts`**
`registry.register()` rejects a strategy without them.

**4. Reject unsupported sources explicitly**
Call `self.supports(source)` first and return a clear `success=False` message
rather than letting an `AttributeError` surface from deep inside the engine.

**5. Keep strategies stateless**
Registered instances are shared singletons. Never store request data on `self`.
Engine-level state (like the Playwright browser) lives in its own module.

**6. Never return engine-specific objects**
The output is always plain `bytes`.

---

## 🧪 Testing your strategy

```python
# tests/test_my_engine.py
from django.test import SimpleTestCase, override_settings
from unittest.mock import patch
from base.modules.pdfEngine.registry import registry
from base.modules.pdfEngine.source import HtmlSource, DataSource
from base.modules.pdfEngine.your_engine import MyEnginePdfStrategy


class MyEnginePdfStrategyTest(SimpleTestCase):

    def setUp(self):
        self.strategy = MyEnginePdfStrategy()

    def test_declares_contract(self):
        self.assertEqual(self.strategy.name, "myengine")
        self.assertIn(HtmlSource, self.strategy.accepts)

    def test_rejects_unsupported_source(self):
        result = self.strategy.generate(DataSource(data={}))
        self.assertFalse(result.success)
        self.assertIn("only accepts", result.message)

    @patch("my_engine.render", return_value=b"%PDF-1.7 fake")
    def test_generate_success(self, _):
        result = self.strategy.generate(HtmlSource(html="<h1>Hi</h1>"))
        self.assertTrue(result.success)
        self.assertTrue(result.pdf_bytes.startswith(b"%PDF"))

    @patch("my_engine.render", side_effect=RuntimeError("boom"))
    def test_generate_never_raises(self, _):
        result = self.strategy.generate(HtmlSource(html="<h1>Hi</h1>"))
        self.assertFalse(result.success)
        self.assertIn("boom", result.message)


class RegistryTest(SimpleTestCase):

    def setUp(self):
        registry.clear()

    def tearDown(self):
        registry.clear()

    def test_alias_resolves_to_registered_strategy(self):
        registry.register(MyEnginePdfStrategy())
        with override_settings(PDF_STRATEGY_ALIASES={"transcript": "myengine"}):
            self.assertEqual(registry.get("transcript").name, "myengine")

    def test_unknown_name_raises(self):
        with self.assertRaises(LookupError):
            registry.get("nope")

    def test_duplicate_name_rejected(self):
        registry.register(MyEnginePdfStrategy())
        with self.assertRaises(ValueError):
            registry.register(MyEnginePdfStrategy())
```

Call `registry.clear()` in `setUp`/`tearDown` so registrations don't leak between tests.

---

## 🩺 Troubleshooting

| Symptom                                            | Likely cause                                                                 |
| -------------------------------------------------- | ---------------------------------------------------------------------------- |
| `LookupError: No PDF strategy registered as 'x'`   | Not registered in `ready()`, or typo in `PDF_STRATEGY_ALIASES`               |
| `ValueError: ... already registered`               | Two apps claim the same `name`, or `ready()` ran twice (use `override=True`) |
| `success=False`, "only accepts ... got DataSource" | Alias points at an engine that can't consume the source the view builds      |
| Images/CSS missing in WeasyPrint output            | `base_url` not passed in `HtmlSource`                                        |
| `cannot load library 'libgobject-2.0-0'` (Windows) | WeasyPrint's GTK runtime missing. Use Playwright, WSL2, or Docker            |
| Playwright works locally, fails on deploy          | Chromium not installed at build time. Check `playwright install` in build    |

---

## 🔗 Where to Go Next

| Topic                       | Document                                                                       |
| --------------------------- | ------------------------------------------------------------------------------ |
| 📐 Strategy contract        | [base.py](../../../base/modules/pdfEngine/base.py)                             |
| 🧩 Source types             | [source.py](../../../base/modules/pdfEngine/source.py)                         |
| 📋 Registry pattern         | [registry.py](../../../base/modules/pdfEngine/registry.py)                     |
| 🎭 Reference implementation | [examples/playwight.py](../../../base/modules/pdfEngine/examples/playwight.py) |
| 💳 Sibling module           | [Payments Module](./payments.md)                                               |
