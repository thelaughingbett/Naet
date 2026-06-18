# 🔔 Notifications Module

> How the portal sends emails and SMS messages — payment confirmations,
> result alerts, fee reminders, enrollment approvals. One service, two
> channels, fully swappable backends. A bad template or a flaky provider
> never breaks a student-facing request.

---

## 🗺️ Overview

Nothing in the codebase talks to a mail server or SMS gateway directly.
Every outbound message goes through `NotificationService.send()`, which
renders the template, picks the right backend from the registry, and
dispatches. One channel failing never kills the other.

```
Something happens (payment confirmed, results published, deferment filed…)
      ↓
NotificationService.send(user, template_key, channels, context)
      ↓
render_email / render_sms          ← templates.py renders before the backend is called
      ↓
notification_registry.get_email()  ← looks up the single registered backend
notification_registry.get_sms()
      ↓
backend.send(EmailPayload / SMSPayload)   ← provider-specific delivery
      ↓
NotificationResult(success, message_id, …)   ← logged; never raised to caller
```

Unlike the ERP registry (which stores a list of handlers per event),
the notification registry holds **exactly one email backend and one SMS
backend** at a time. The institution configures them once at startup and
every `send()` call uses them.

---

## 🏗️ Architecture

```
base/modules/notifications/
├── __init__.py              ← public exports: NotificationService, notification_registry
├── base.py                  ← NotificationResult dataclass
├── registry.py              ← NotificationRegistry singleton
├── templates.py             ← NOTIFICATION_TEMPLATES, render_email, render_sms
├── service.py               ← NotificationService — the only call site
│
├── email/
│   ├── __init__.py
│   ├── base.py              ← EmailPayload + AbstractEmailBackend
│   └── backends/
│       ├── __init__.py
│       ├── messagepit.py    ← dev: SMTP capture (port 1025)
│       ├── examples/
│       │   └── backends.sendgrid.example.py
│       └── contrib/         ← community backends
│
└── sms/
    ├── __init__.py
    ├── base.py              ← SMSPayload + AbstractSMSBackend
    └── backends/
        ├── __init__.py
        ├── africastalking.py ← prod: Africa's Talking (Kenya)
        ├── messagepit.py     ← dev: Twilio-compatible capture (port 8200)
        ├── examples/
        │   └── backends.africastalking.example.py
        └── contrib/          ← community backends
```

---

## 📐 The Contract

### `NotificationService.send()`

```python
NotificationService.send(
    user=student.user,
    template_key='payment_confirmed',
    channels=['email', 'sms'],
    context={
        'student_name': student.user.full_name,
        'amount':       payment.amount,
        'ref':          payment.transaction_ref,
        'balance':      account.balance,
    }
)
```

- Never raises — logs failures and moves on.
- A missing backend is a warning, not an error.
- A failure on `email` does not affect `sms`, and vice versa.

### `NotificationResult`

```python
@dataclass
class NotificationResult:
    success:      bool
    message_id:   Optional[str] = None   # provider's message ID on success
    message:      str = ""               # human-readable status or error
    raw_response: Optional[dict] = None  # full provider response, for debugging
```

### `EmailPayload` / `SMSPayload`

Constructed exclusively by `NotificationService` — backends never build them.

```python
EmailPayload(
    to_address   = 'student@example.com',
    subject      = 'Payment Confirmed — KES 5000',   # pre-rendered
    html_body    = '<p>…</p>',                        # pre-rendered
    text_body    = 'Payment of KES 5000 confirmed.',  # always required
    from_address = 'noreply@university.ac.ke',
)

SMSPayload(
    to_number = '+254712345678',   # E.164 format
    body      = 'Your payment of KES 5000 has been confirmed. Ref: TXN-001.',
    sender_id = 'NAET-PORTAL',    # optional shortcode
)
```

---

## 📋 Available Templates

| Key                    | Channels    | Required context keys      |
| ---------------------- | ----------- | -------------------------- |
| `payment_confirmed`    | email + sms | `amount`, `ref`, `balance` |
| `payment_failed`       | email + sms | `amount`                   |
| `results_published`    | email + sms | `session`                  |
| `reporting_confirmed`  | email + sms | `session`, `student_name`  |
| `fee_reminder`         | email + sms | `balance`, `due_date`      |
| `enrollment_approved`  | email + sms | `session`                  |
| `registration_success` | email + sms | _(none beyond `user`)_     |

Templates live in `NOTIFICATION_TEMPLATES` in `templates.py`. Email
templates reference Django template files under
`base/notifications/email/`; SMS templates are inline format strings.

### Adding a Template

Add its entry to `NOTIFICATION_TEMPLATES` — no other changes needed:

```python
'deferment_received': {
    'email': {
        'subject': 'Deferment Request Received — {session}',
        'html':    'base/notifications/email/deferment_received.html',
        'text':    'base/notifications/email/deferment_received.txt',
    },
    'sms': 'Your deferment request for {session} has been received. Ref: {ref}.',
},
```

---

## 🔄 Backend Lifecycle

```
AppConfig.ready()
      ↓
notification_registry.register_email(backend)   ← validates provider_name
notification_registry.register_sms(backend)     ← rejects blank provider_name
      ↓
NotificationService._send_email / _send_sms
      ↓
notification_registry.get_email() / get_sms()   ← raises RuntimeError if not registered
      ↓
backend.send(payload)                            ← must never raise; returns NotificationResult
      ↓
logger.info / logger.error                       ← all outcomes logged; caller unaffected
```

---

## 🛠️ Registration Patterns

### Pattern A — Environment switching (recommended)

```python
# base/apps.py
class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        from django.conf import settings
        from base.modules.notifications.registry import notification_registry

        if settings.DEBUG:
            from base.modules.notifications.email.backends.messagepit import MessagePitEmailBackend
            from base.modules.notifications.sms.backends.messagepit import MessagePitSMSBackend
            notification_registry.register_email(MessagePitEmailBackend())
            notification_registry.register_sms(MessagePitSMSBackend())
        else:
            from base.modules.notifications.email.backends.sendgrid import SendGridEmailBackend
            from base.modules.notifications.sms.backends.africastalking import AfricasTalkingBackend
            notification_registry.register_email(SendGridEmailBackend())
            notification_registry.register_sms(AfricasTalkingBackend())
```

### Pattern B — Static (single environment)

```python
notification_registry.register_email(SendGridEmailBackend())
notification_registry.register_sms(AfricasTalkingBackend())
```

---

## 🛠️ Adding a New Backend

### Step 1 — Decide where your file lives

Institution-specific (your school's actual provider):

```
base/modules/notifications/email/backends/mailgun.py
base/modules/notifications/sms/backends/vonage.py
```

Community contribution (reusable for a named provider):

```
base/modules/notifications/email/backends/contrib/mailgun.py
base/modules/notifications/sms/backends/contrib/vonage.py
```

### Step 2 — Implement the contract

**Email:**

```python
from base.modules.notifications.email.base import AbstractEmailBackend, EmailPayload
from base.modules.notifications.base import NotificationResult

class MailgunEmailBackend(AbstractEmailBackend):
    provider_name = "mailgun"   # required — registry rejects blank

    def send(self, payload: EmailPayload) -> NotificationResult:
        try:
            response = requests.post(
                f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
                auth=("api", settings.MAILGUN_API_KEY),
                data={
                    "from":    payload.from_address,
                    "to":      payload.to_address,
                    "subject": payload.subject,
                    "html":    payload.html_body,
                    "text":    payload.text_body,
                },
                timeout=10,
            )
            data = response.json()
            return NotificationResult(
                success=response.status_code == 200,
                message_id=data.get("id"),
                raw_response=data,
            )
        except Exception as e:
            return NotificationResult(success=False, message=str(e))
```

**SMS:**

```python
from base.modules.notifications.sms.base import AbstractSMSBackend, SMSPayload
from base.modules.notifications.base import NotificationResult

class VonageSMSBackend(AbstractSMSBackend):
    provider_name = "vonage"

    def send(self, payload: SMSPayload) -> NotificationResult:
        try:
            # call Vonage API
            return NotificationResult(success=True, message_id="...")
        except Exception as e:
            return NotificationResult(success=False, message=str(e))
```

### Step 3 — Register it in `apps.py`

```python
from base.modules.notifications.email.backends.mailgun import MailgunEmailBackend
notification_registry.register_email(MailgunEmailBackend())
```

### Step 4 — Add settings

```python
# settings.py
MAILGUN_API_KEY = "key-xxx"
MAILGUN_DOMAIN  = "mg.university.ac.ke"
```

---

## 🧪 Local Development — MessagePit

With `DEBUG=True` and MessagePit running locally, every outbound message
is captured in the local UI — no real emails or texts are sent.

| Channel | View at                       | Port |
| ------- | ----------------------------- | ---- |
| Email   | http://localhost:8025 (Inbox) | 1025 |
| SMS     | http://localhost:8025 (SMS)   | 8200 |

Payloads are identical to what production would send, so you can verify
rendering and content before deploying.

```python
# settings.py (defaults shown — only set if you need non-defaults)
MESSAGEPIT_SMTP_HOST = 'localhost'
MESSAGEPIT_SMTP_PORT = 1025
MESSAGEPIT_SMS_URL   = 'http://localhost:8200'
```

---

## 🚦 The Golden Rules

**1. `send()` must never raise**
Catch all exceptions and return `NotificationResult(success=False, message=str(e))`.
The service layer logs the failure; the caller never sees it.

**2. `send()` must never render templates**
Receive subject, html_body, and text_body via `EmailPayload` as fully
rendered strings. SMS body arrives via `SMSPayload.body` ready to send.

**3. `send()` must never write to the database**
Audit trails belong to the service layer or the calling service, not
inside a backend.

**4. Always set `provider_name`**
The registry rejects registration without one.

**5. Always send both `html_body` and `text_body`**
Never HTML-only — some mail clients render plain text only.

---

## 🧪 Testing Your Backend

```python
# tests/test_mailgun_backend.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from base.modules.notifications.email.backends.mailgun import MailgunEmailBackend
from base.modules.notifications.email.base import EmailPayload


class MailgunBackendTest(TestCase):

    def setUp(self):
        self.backend = MailgunEmailBackend()
        self.payload = EmailPayload(
            to_address='student@example.com',
            subject='Test Subject',
            html_body='<p>Hello</p>',
            text_body='Hello',
        )

    @patch('base.modules.notifications.email.backends.mailgun.requests.post')
    def test_send_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'id': 'msg-001'}

        result = self.backend.send(self.payload)

        self.assertTrue(result.success)
        self.assertEqual(result.message_id, 'msg-001')

    @patch('base.modules.notifications.email.backends.mailgun.requests.post')
    def test_send_returns_failure_on_exception(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")

        result = self.backend.send(self.payload)

        self.assertFalse(result.success)
        self.assertIn("Connection refused", result.message)

    def test_provider_name_set(self):
        self.assertEqual(self.backend.provider_name, 'mailgun')
```

---

## 🔗 Where to Go Next

| Topic                                   | Document                                  |
| --------------------------------------- | ----------------------------------------- |
| 🏢 ERP sync (same registry pattern)     | [ERP Module](erp/index.md)                |
| 💳 Payments (calls NotificationService) | [Payments Module](payments/index.md)      |
| 📋 Registry source                      | `base/modules/notifications/registry.py`  |
| 📐 Abstract base classes                | `email/base.py`, `sms/base.py`            |
| 🗂️ Template definitions                 | `base/modules/notifications/templates.py` |

---

> 🔗 Back to [Module Breakdown](../README.md)
