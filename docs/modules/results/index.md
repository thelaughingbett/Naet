# 📊 Results Import Module

> How exam and CAT scores get from wherever they're produced — a lecturer's
> spreadsheet, a push from an LMS like Moodle or Canvas, a custom grading
> system — into the student portal as `Result` rows. Add a new source
> without touching how results actually get validated, resolved, or saved.
> Think of it as the same pattern as the news and ERP modules: a strategy
> reads and normalises, the core owns every write.

---

## 🗺️ Overview

```
External source (Excel upload, LMS push, custom integration)
      ↓
AbstractResultsStrategy.load()      ← your strategy normalises raw rows/payloads
      ↓
ResultImportResult                  ← a list of ResultEntry objects + warnings
      ↓
run_results_import()                ← validates, resolves student/curriculum, writes Result rows
      ↓
Student sees their result on the portal
```

Strategies never touch the database. They take whatever shape the source
data is in — spreadsheet rows, JSON payload, anything else — and hand
back a clean, normalised list. Everything after that (matching a
registration number to an actual student, checking the unit was
actually approved for enrollment, and the database write itself) is
handled in exactly one place.

---

## 🏗️ Architecture

```
base/modules/results/
├── base.py                  # the contract: AbstractResultsStrategy, ResultEntry, ResultImportResult
├── service.py                 # run_results_import() — the only place that writes Result rows
└── strategies/
    ├── excel.py                 # ExcelResultsStrategy — spreadsheet upload
    └── lms_push.py                # LMSPushStrategy — JSON push from an LMS
```

---

## 📐 The Contract

```python
class AbstractResultsStrategy(ABC):

    @abstractmethod
    def load(self, session, **kwargs) -> ResultImportResult:
        """
        Load results for the given session from wherever this strategy reads from.
        kwargs are strategy-specific — e.g. source=file_object, payload=request.data.
        Must always return a ResultImportResult. Must never raise.
        """
        raise NotImplementedError

    def validate(self, result: ResultImportResult) -> list[str]:
        """
        Runs basic structural checks (missing fields, invalid result_type,
        non-numeric scores) before anything is written. Override to layer
        on strategy-specific validation.
        """
        ...
```

A strategy is responsible for exactly one thing: turning its source data
into a list of `ResultEntry` objects. Everything else — matching those
entries to real students and curriculum entries, enforcing that only
approved enrollments receive results, and the actual write — lives in
`run_results_import()`.

### 📦 The dataclasses

**`ResultEntry`** — the normalised shape of one result record:

| Field                 | Purpose                                                           |
| --------------------- | ----------------------------------------------------------------- |
| `registration_number` | Identifies the student                                            |
| `course_code`         | Identifies the curriculum entry                                   |
| `result_type`         | `'C'` (CAT) or `'E'` (Exam)                                       |
| `score`               | The numeric score, e.g. `68.50`                                   |
| `title`               | A label for this specific result, e.g. `"CAT 1"`, `"Final Exam"`  |
| `meta`                | Optional dict — anything a strategy wants to attach for debugging |

**`ResultImportResult`** — returned by every strategy after a `load()` call:

| Field      | Purpose                                                           |
| ---------- | ----------------------------------------------------------------- |
| `success`  | `False` means nothing was written — the caller should not proceed |
| `entries`  | The proposed `ResultEntry` list                                   |
| `message`  | Human-readable summary or error                                   |
| `warnings` | Non-fatal issues — e.g. `"REG/001/2024 not found — skipped"`      |
| `stats`    | Optional metadata, e.g. `{"rows_read": 120, "rows_skipped": 3}`   |

---

## 🧰 Built-in Strategies

| Strategy               | Source                            | Notes                                                                                                                               |
| ---------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `ExcelResultsStrategy` | An uploaded `.xlsx` file          | Reads `registration_number \| course_code \| result_type \| score \| title` columns; configurable sheet and header row via settings |
| `LMSPushStrategy`      | A JSON payload pushed from an LMS | Designed to sit behind a `POST /api/results/` view; parses a `results` list from the request body                                   |

Both ship with the same shape: parse what's there, skip and warn on rows
that don't fit, and never decide on their own whether a row is "close
enough" to accept — that judgment stays with validation and the
resolution step.

---

## 🛠️ Adding a New Strategy

### Step 1 — Create your strategy file

```
base/modules/results/strategies/your_source.py
```

### Step 2 — Implement the contract

```python
# base/modules/results/strategies/your_source.py

from base.modules.results.base import (
    AbstractResultsStrategy,
    ResultEntry,
    ResultImportResult,
)


class YourSourceResultsStrategy(AbstractResultsStrategy):
    """
    Imports results from <wherever your source is>.
    """

    def load(self, session, **kwargs) -> ResultImportResult:
        try:
            raw_rows = self._fetch(kwargs)
        except Exception as e:
            return ResultImportResult(success=False, message=str(e))

        entries, warnings = [], []

        for i, row in enumerate(raw_rows):
            try:
                entries.append(ResultEntry(
                    registration_number=row['reg_no'],
                    course_code=row['course'].upper(),
                    result_type=row['type'].upper(),
                    score=float(row['score']),
                    title=row['title'],
                ))
            except (KeyError, ValueError) as e:
                warnings.append(f"Row {i}: {e} — skipped")

        return ResultImportResult(
            success=True,
            entries=entries,
            warnings=warnings,
            message=f"Parsed {len(entries)} results.",
        )
```

### Step 3 — Point settings at it

```python
# settings.py
RESULTS_STRATEGY = 'base.modules.results.strategies.your_source.YourSourceResultsStrategy'
```

`run_results_import()` resolves this dotted path via `import_string()`
at call time, so switching sources is a one-line settings change with no
core code to touch.

---

## 🔁 From Strategy Output to Database Rows

`run_results_import(session, **kwargs)` is the single entry point that
actually writes `Result` records, and it runs the same pipeline
regardless of which strategy produced the entries:

1. **Load** — call the configured strategy's `load(session, **kwargs)`.
2. **Validate** — run `strategy.validate(result)`; any structural errors
   abort the import before anything touches the database.
3. **Resolve** — match each entry's `registration_number` to a `Student`
   and `course_code` to a `Curriculum` entry for that session.
4. **Authorise** — only entries where the student has an _approved_
   enrollment for that curriculum are kept; everything else becomes a
   warning rather than a hard failure.
5. **Write** — the surviving rows are upserted in a single atomic
   transaction, so a result re-import updates existing rows instead of
   duplicating them.

The function returns `(success, message, count_created)`, with any
skipped rows folded into the warning count in the message rather than
failing the whole import — a few unmatched rows in a spreadsheet of
hundreds shouldn't block everyone else's results from landing.

---

## 🚦 The Golden Rules

**1. Strategies normalise — they never persist**
`load()` returns data; `run_results_import()` is the only code path that
writes a `Result` row.

**2. `load()` always returns a result object — it never raises**
Catch exceptions internally and return `ResultImportResult(success=False, message=...)`
instead of letting anything propagate.

**3. Skippable rows are warnings, not failures**
A missing student or an unrecognised course code means that one row
doesn't get imported — it doesn't mean the whole batch fails. Reserve
`success=False` for input that's unreadable or unusable as a whole.

**4. Never clamp or silently rewrite a score**
If a score looks out of range, flag it with a warning and pass it
through as-is. Deciding what to do about it belongs to validation or a
human reviewer, not the strategy.

**5. Only approved enrollments receive results**
A score for a unit the student was never approved to take is treated
the same as a row that didn't resolve — skipped, with a warning, not
silently written.

---

## 🧪 Testing your strategy

```python
# tests/test_lms_push_strategy.py
from django.test import TestCase
from base.modules.results.strategies.lms_push import LMSPushStrategy


class LMSPushStrategyTest(TestCase):

    def setUp(self):
        self.strategy = LMSPushStrategy()

    def test_load_parses_valid_payload(self):
        payload = {
            "results": [
                {
                    "registration_number": "CS/001/2024",
                    "course_code": "csc411",
                    "result_type": "e",
                    "score": 72.5,
                    "title": "Final Exam",
                }
            ]
        }

        result = self.strategy.load(session=None, payload=payload)

        self.assertTrue(result.success)
        self.assertEqual(len(result.entries), 1)

        entry = result.entries[0]
        self.assertEqual(entry.course_code, "CSC411")
        self.assertEqual(entry.result_type, "E")

    def test_load_warns_on_malformed_item(self):
        payload = {"results": [{"registration_number": "CS/001/2024"}]}

        result = self.strategy.load(session=None, payload=payload)

        self.assertTrue(result.success)
        self.assertEqual(len(result.entries), 0)
        self.assertEqual(len(result.warnings), 1)

    def test_load_rejects_missing_payload(self):
        result = self.strategy.load(session=None)
        self.assertFalse(result.success)
```

---

## 🔗 Where to Go Next

| Topic                      | Document                                       |
| -------------------------- | ---------------------------------------------- |
| 📰 News module             | [News Module](news.md)                         |
| 🔌 ERP sync module         | [ERP Module](erp.md)                           |
| 📧 Email generation module | [Email Generation Module](email_generation.md) |
| 💳 Payments module         | [Payments Module](payments.md)                 |
| 🗃️ `Result` model fields   | [Models Reference](../models.md)               |

---

> 🔗 Back to [Documentation Index](../README.md)
