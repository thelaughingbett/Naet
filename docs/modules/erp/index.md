# 🔌 ERP Sync Module

> How changes inside the portal — a payment clearing, an enrollment getting
> approved, a deferment being filed — get pushed out to whatever external
> ERP system the institution actually runs on. And how to add a new
> outbound sync handler without touching a single line of core code.
> Think of this as the outbox layer — async, retrying, fully audited,
> and indifferent to which ERP is on the other end.

---

## 🗺️ Overview

This module doesn't talk to your ERP directly from a view or a signal.
It queues the job, lets the request finish, and lets Celery worry about
retries, backoff, and logging — so a slow or flaky ERP never blocks a
student-facing request.

```
Something happens (Payment confirmed, Enrollment approved, Deferment filed...)
      ↓
dispatch_erp_event(instance, event)   ← called from a signal, view, or service
      ↓
erp_sync.delay(...)                   ← queued on Celery, fires after the DB transaction commits
      ↓
erp_registry.get(event)               ← looks up every handler bound to this event
      ↓
handler.sync(instance)                ← your AbstractERPTask talks to the external ERP
      ↓
ERPSyncLog row written                ← attempting → success / failed / error / exhausted
```

`dispatch_erp_event()` wraps the Celery call in `transaction.on_commit(...)`,
so a sync never fires for a DB row that ends up rolled back.

---

## 🏗️ Architecture

```
base/modules/erp/
├── tasks/
│   ├── __init__.py        # re-exports base + sync
│   ├── base.py             # AbstractERPTask + ERPSyncResult contract
│   ├── sync.py              # erp_sync Celery task — retries, backoff, logging
│   ├── contrib/
│   │   └── tasks/           # community-contributed handlers (SAP, Oracle, Sage, Odoo...)
│   └── examples/
│       └── implementations.py   # reference blueprints only — see note below
├── registry.py             # ERPRegistry singleton
├── dispatch.py              # dispatch_erp_event() helper
└── models.py                 # ERPSyncLog audit trail
```

> ⚠️ **`examples/implementations.py` is reference material, not an import target.**
> The four sample tasks in there (`PaymentERPTask`, `EnrollmentERPTask`,
> `HELBReportingTask`, `DefermentNotificationTask`) are blueprints to copy
> from, the same way `news/backends/contrib/` holds community examples
> rather than production code. Write your institution's real handlers as
> their own files directly under `tasks/` (e.g. `tasks/payments.py`),
> following the **Native Core Implementations** pattern below — not by
> importing the examples module into `apps.py`.
>
> Also double-check import paths if you're copying snippets from inline
> comments elsewhere in this codebase: the actual package root is
> `base.modules.erp.*` — that's what `registry.py`, `dispatch.py`, and
> `sync.py` resolve to internally (via `.tasks.base`, `.tasks.sync`
> relative imports) and what `implementations.py` itself imports from
> (`base.modules.erp.tasks.base`). A few registration examples in module
> docstrings shorthand this as a bare `erp.*` — that path doesn't exist
> as its own top-level package here, so use the `base.modules.erp.*` form
> in your own `apps.py`.

---

## 🔄 The Sync Lifecycle

Every attempt gets its own `ERPSyncLog` row, so you can see exactly what
happened without digging through worker logs.

| Status       | Meaning                                                                   |
| ------------ | ------------------------------------------------------------------------- |
| `attempting` | Logged immediately before `handler.sync(instance)` is called              |
| `success`    | `handler.sync()` returned `ERPSyncResult(success=True)`                   |
| `failed`     | `handler.sync()` returned `ERPSyncResult(success=False)` — a soft failure |
| `error`      | `handler.sync()` raised an exception — a hard failure                     |
| `exhausted`  | Retries hit `max_retries` with no success — the task gives up             |

A `failed` result and a raised exception both end up driving the same
retry path: a soft failure is logged as `failed`, then deliberately
re-raised as an exception inside `_run_handler()` so the exponential
backoff logic kicks in either way. Each handler gets its own independent
retry cycle — one handler exhausting its retries doesn't affect another
handler bound to the same event.

Backoff is computed as:

```python
delay = min(handler.retry_backoff * (2 ** attempt), handler.retry_max_delay)
```

so the wait roughly doubles each attempt until it caps out at
`retry_max_delay`. Both numbers are overridable per task.

---

## 📐 The Contract

```python
class AbstractERPTask(ABC):

    event:    str = ""   # e.g. 'payment.confirmed' — used for registry routing
    model:    str = ""   # e.g. 'Payment' — logging/admin display only
    endpoint: str = ""   # this task's production URL

    max_retries:     int = 5
    retry_backoff:   int = 60     # seconds, before exponential growth
    retry_max_delay: int = 3600   # hard cap on the backoff delay

    def get_endpoint(self) -> str:
        """
        In DEBUG, redirects HTTP calls to MessagePit's webhook capture
        server (port 8300) instead of the real ERP — same path, different
        host, so you can see exactly what would have been sent.
        """
        ...

    @abstractmethod
    def sync(self, instance) -> ERPSyncResult:
        """
        Push `instance` to the external ERP.
        Raise on hard failure, or return ERPSyncResult(success=False)
        for an expected/soft failure. Both retry the same way.
        """
        raise NotImplementedError

    def get_instance_ref(self, instance) -> str:
        """Human-readable reference for logging — override if needed."""
        ...
```

### 📦 The dataclass

```python
@dataclass
class ERPSyncResult:
    success:      bool
    message:      str = ""
    external_ref: Optional[str] = None   # the ERP's own ID for this record
    raw_response: Optional[dict] = None  # stored on the log row for debugging
```

### 🗃️ `ERPSyncLog` fields

| Field              | Purpose                                      |
| ------------------ | -------------------------------------------- |
| `content_type_str` | Generic reference, e.g. `"Payment:3fa9-..."` |
| `event`            | The event string that triggered this sync    |
| `handler`          | Class name of the handler that ran           |
| `attempt`          | Which retry attempt this row represents      |
| `status`           | One of the five lifecycle states above       |
| `message`          | Human-readable result or error message       |
| `external_ref`     | The ID the ERP gave back, if any             |
| `raw_response`     | Full JSON response, for debugging            |

---

## 🛠️ Adding a New Handler

### Step 1 — Decide where your file lives

Community contribution (a reusable integration for a named ERP product):

```
base/modules/erp/tasks/contrib/tasks/sap.py
```

Institution-specific (your school's actual production endpoint):

```
base/modules/erp/tasks/payments.py
```

### Step 2 — Implement the contract

```python
# base/modules/erp/tasks/payments.py

import requests
from django.conf import settings

from base.modules.erp.tasks.base import AbstractERPTask, ERPSyncResult


class PaymentERPTask(AbstractERPTask):
    event    = 'payment.confirmed'
    model    = 'Payment'
    endpoint = 'https://erp.university.ac.ke/api/payments/'

    def sync(self, instance) -> ERPSyncResult:
        response = requests.post(
            self.get_endpoint(),
            json={
                'ref':     instance.transaction_ref,
                'amount':  str(instance.amount),
                'student': instance.account.student.registration_number,
            },
            headers={'Authorization': f'Bearer {settings.ERP_API_KEY}'},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        return ERPSyncResult(
            success=True,
            external_ref=data.get('id'),
            raw_response=data,
        )
```

Letting `requests` exceptions propagate is fine here — `sync()` is allowed
to raise; `_run_handler()` catches it, logs `error`, and schedules a retry.

### Step 3 — Register it

```python
# base/apps.py
class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        from base.modules.erp.registry import erp_registry
        from base.modules.erp.tasks.payments import PaymentERPTask

        erp_registry.register(PaymentERPTask())
```

### Step 4 — Add settings

```python
# settings.py
ERP_API_KEY          = "your-erp-bearer-token"
MESSAGEPIT_WEBHOOK_URL = "http://localhost:8300"   # DEBUG-mode capture target
```

### Step 5 — Fire it from wherever the state actually changes

```python
from base.modules.erp.dispatch import dispatch_erp_event

dispatch_erp_event(payment, 'payment.confirmed')
```

This is usually called from a model's `save()` override, a signal
receiver, or a service method — wherever the instance is known to be in
its final, committed state.

---

## 🔄 The Sync Flow, Step by Step

```
dispatch_erp_event(instance, event) called
      ↓
transaction.on_commit(...) schedules erp_sync.delay(...)
      ↓
erp_sync task resolves the model + instance via apps.get_model(app_label, model_name)
      ↓
erp_registry.get(event) returns every handler bound to that event
      ↓
each handler runs through _run_handler() — its own ERPSyncLog row, its own retry cycle
      ↓
success → log.status = 'success'
failed/error → exponential backoff retry → eventually 'success' or 'exhausted'
```

Because the model and instance are resolved by string (`app_label`,
`model_name`, `instance_id`) rather than passed as a live object, the
task survives a worker restart between when it's queued and when it runs.

---

## 🧪 Local Testing — MessagePit Capture

You don't need a real ERP sandbox to develop against. With `DEBUG=True`,
`get_endpoint()` rewrites every handler's URL to point at MessagePit's
webhook capture server instead, keeping the original path so you can
still tell requests apart:

```
Real:  https://erp.university.ac.ke/api/payments/
DEBUG: http://localhost:8300/api/payments/
```

Run MessagePit locally and you'll see every outbound ERP call land there
exactly as it would have been sent — headers, body, and all — without
risking a real write to production systems while you're building a
handler.

---

## 🔗 Event Naming Convention

Stick to the `model.action` pattern so the registry stays predictable:

| Domain     | Example events                                                   |
| ---------- | ---------------------------------------------------------------- |
| Financial  | `payment.confirmed`, `payment.failed`                            |
| Academic   | `enrollment.approved`, `enrollment.rejected`, `result.published` |
| Lifecycle  | `deferment.created`, `deferment.reinstated`, `student.graduated` |
| Regulatory | `reporting.submitted`                                            |

Multiple handlers can bind to the same event — the registry stores a list
per key, and `erp_sync` runs every handler in that list.

---

## 🚦 The Golden Rules

**1. `sync()` only talks to the external API — it never touches local DB state**
All `ERPSyncLog` writes are owned by `_run_handler()`. Your handler's job
is the network conversation, nothing else.

**2. Soft failures and hard failures both retry — pick whichever fits**
Return `ERPSyncResult(success=False, message=...)` for an expected
rejection (e.g. the ERP validated the payload and said no). Let an
exception propagate for anything unexpected (timeouts, connection
errors, malformed responses). Both paths hit the same backoff logic.

**3. `event` strings are matched exactly**
The registry does plain dict lookups — no wildcards, no fuzzy matching.
A typo in `event` means the handler silently never fires (the task logs
"No handlers for event '...' — skipping" and returns).

**4. Don't import directly from `tasks/examples/implementations.py`**
Those four classes are there to read and copy, not to register as-is —
copy the relevant one into its own file under `tasks/` first, the same
way `news` keeps community/example code separate from what actually runs.

**5. `max_retries` / `retry_backoff` / `retry_max_delay` are per-task**
Override them on your subclass if an endpoint needs a longer timeout
window or fewer retries than the defaults (5 retries, 60s base backoff,
1hr cap).

---

## 🧪 Testing your handler

```python
# tests/test_erp_payment_task.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from base.modules.erp.tasks.payments import PaymentERPTask


class PaymentERPTaskTest(TestCase):

    def setUp(self):
        self.task = PaymentERPTask()

    @patch('base.modules.erp.tasks.payments.requests.post')
    def test_sync_success(self, mock_post):
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {'id': 'erp-9001'}

        instance = MagicMock()
        instance.transaction_ref = 'TXN-123'
        instance.amount = 500
        instance.account.student.registration_number = 'Lit/035/34'

        result = self.task.sync(instance)

        self.assertTrue(result.success)
        self.assertEqual(result.external_ref, 'erp-9001')

    @patch('base.modules.erp.tasks.payments.requests.post')
    def test_sync_raises_on_network_error(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")

        with self.assertRaises(Exception):
            self.task.sync(MagicMock())

    def test_event_and_endpoint_set(self):
        self.assertEqual(self.task.event, 'payment.confirmed')
        self.assertTrue(self.task.endpoint.startswith('https://'))
```

---

## 🔗 Where to Go Next

| Topic                                  | Document                         |
| -------------------------------------- | -------------------------------- |
| 📰 News module (same registry pattern) | [News Module](news.md)           |
| 💳 Payments module                     | [Payments Module](payments.md)   |
| 🗃️ `ERPSyncLog` model fields           | [Models Reference](../models.md) |
| 📋 Registry pattern                    | `base/modules/erp/registry.py`   |
| 🔄 Celery sync task                    | `base/modules/erp/tasks/sync.py` |

---

> 🔗 Back to [Documentation Index](../README.md)
