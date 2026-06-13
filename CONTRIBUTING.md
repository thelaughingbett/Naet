# 🤝 Contributing to Naet

> First off — thank you for being here. This project is an open source
> template for building school management systems, particularly for
> institutions in Africa. Every contribution, big or small, makes it
> more useful for more people.

---

## 📑 Contents

- [How the project is structured](#-how-the-project-is-structured)
- [Ways to contribute](#-ways-to-contribute)
- [Adding a payment backend](#-adding-a-payment-backend)
- [Adding an ERP task](#-adding-an-erp-task)
- [Adding a notification backend](#-adding-a-notification-backend)
- [Adding an email strategy](#-adding-an-email-strategy)
- [Adding an events backend](#-adding-an-events-backend)
- [Adding a news backend](#-adding-a-news-backend)
- [Writing tests](#-writing-tests)
- [Writing docs](#-writing-docs)
- [Submitting a pull request](#-submitting-a-pull-request)
- [Code style](#-code-style)
- [Reporting bugs](#-reporting-bugs)

---

## 🏗️ How the project is structured

```
studentsportal/
├── base/                   ← core models, mixins, signals
├── erp/                    ← ERP integration layer (generic)
├── payments/               ← payment backend layer (generic)
├── notifications/          ← notification engine (generic)
├── utils/                  ← shared utilities (email generator etc)
├── contrib/                ← reference implementations
│   ├── payments/           ← MpesaBackend, EquityBankBackend etc
│   ├── erp/                ← UniversityERPTask etc
│   └── notifications/      ← AfricasTalkingBackend etc
├── examples/               ← minimal working examples for each extension point
└── docs/                   ← full system documentation
```

**The rule:** core packages (`erp/`, `payments/`, `notifications/`) contain
only abstract contracts and generic orchestration. No provider-specific code
ever lives in core. Implementations go in `contrib/` or the integrator's own app.

---

## 🌱 Ways to contribute

You don't have to write code to contribute meaningfully.

| Type                | Examples                                                            |
| ------------------- | ------------------------------------------------------------------- |
| 🔌 New backend      | M-Pesa, Stripe, Flutterwave, Airtel Money payment backends          |
| 🔄 New ERP task     | HELB API, KRA, custom university ERP integrations                   |
| 📡 New notification | Email via SendGrid, WhatsApp, push notifications                    |
| 🐛 Bug fix          | Anything in the issue tracker labelled `bug`                        |
| 📋 New feature      | Anything labelled `help wanted`                                     |
| 📄 Documentation    | Fix a typo, clarify an explanation, add an example                  |
| 🧪 Tests            | We always need more coverage — see [Writing tests](#-writing-tests) |
| 🌍 Localisation     | Adapting defaults for a different country's context                 |
| 💬 Discussion       | Opening an issue to propose something or ask a question             |

---

## 🔌 Adding a Payment Backend

The most common contribution. If your institution uses a payment provider
that isn't covered yet, here's how to add it.

### 1. Create your backend file

```
contrib/payments/my_provider.py
```

### 2. Implement `AbstractPaymentBackend`

```python
# contrib/payments/my_provider.py

from payments.backends.base import (
    AbstractPaymentBackend,
    PaymentInitiationResult,
    WebhookVerificationResult,
)


class MyProviderBackend(AbstractPaymentBackend):
    """
    Payment backend for MyProvider.

    Configuration (add to settings.py):
        MY_PROVIDER_API_KEY    = 'your-api-key'
        MY_PROVIDER_SECRET     = 'your-secret'
        MY_PROVIDER_CALLBACK   = 'https://yourdomain.com/payments/webhook/myprovider/'
    """

    method = 'myprovider'  # must be unique across all registered backends

    def initiate(self, payment, **kwargs) -> PaymentInitiationResult:
        """
        Start the payment. What this means depends on the provider:
        - Push-based (M-Pesa): send a push and return the provider ref
        - Redirect-based (bank portal): return a redirect_url
        - Synchronous (cash): return success immediately

        DO NOT update the payment record here.
        Return a PaymentInitiationResult and let the core handle it.
        """
        from django.conf import settings
        import requests

        try:
            response = requests.post(
                'https://api.myprovider.com/charge',
                json={
                    'amount':    str(payment.amount),
                    'reference': str(payment.account.student.registration_number),
                    'callback':  settings.MY_PROVIDER_CALLBACK,
                },
                headers={'Authorization': f"Bearer {settings.MY_PROVIDER_API_KEY}"},
                timeout=30
            )
            data = response.json()

            if response.status_code == 200:
                return PaymentInitiationResult(
                    success=True,
                    provider_ref=data.get('charge_id'),
                    message='Payment initiated — awaiting confirmation',
                    raw_response=data
                )

            return PaymentInitiationResult(
                success=False,
                message=data.get('error', 'Initiation failed'),
                raw_response=data
            )

        except Exception as e:
            return PaymentInitiationResult(
                success=False,
                message=str(e)
            )

    def verify_webhook(self, request) -> WebhookVerificationResult:
        """
        Parse and verify an incoming webhook from the provider.

        1. Verify the signature — reject anything that doesn't match
        2. Extract the transaction ref and provider ref
        3. Return WebhookVerificationResult

        DO NOT update any records here. Just verify and extract.
        """
        import json
        import hmac
        import hashlib
        from django.conf import settings

        # verify signature
        signature = request.headers.get('X-MyProvider-Signature', '')
        expected  = hmac.new(
            settings.MY_PROVIDER_SECRET.encode(),
            request.body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            return WebhookVerificationResult(
                valid=False,
                message='Invalid signature'
            )

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return WebhookVerificationResult(valid=False, message='Invalid JSON')

        # check if the payment succeeded
        if body.get('status') != 'success':
            return WebhookVerificationResult(
                valid=False,
                provider_ref=body.get('charge_id'),
                message=body.get('failure_reason', 'Payment not successful')
            )

        return WebhookVerificationResult(
            valid=True,
            transaction_ref=body.get('transaction_id'),
            provider_ref=body.get('charge_id'),
            amount=body.get('amount'),
            raw_payload=body
        )
```

### 3. Register it in `apps.py`

```python
def ready(self):
    from payments.registry import registry
    from contrib.payments.my_provider import MyProviderBackend
    registry.register(MyProviderBackend())
```

### 4. Add an example

```
examples/payments/my_provider_example.py
```

Keep the example minimal — show the happy path, document the settings needed.

### 5. Add docs

```
docs/extending/payment-backends.md  ← add a row to the table
```

---

## 🔄 Adding an ERP Task

ERP tasks sync model instances to external systems when events happen.
They are not limited to payments — any model can fire an ERP event.

### 1. Create your task file

```
contrib/erp/my_system.py
```

### 2. Implement `AbstractERPTask`

```python
# contrib/erp/my_system.py

from erp.tasks.base import AbstractERPTask, ERPSyncResult


class MySystemPaymentTask(AbstractERPTask):
    """
    Syncs confirmed payments to MySystem ERP.

    Configuration:
        MY_SYSTEM_BASE_URL = 'https://erp.myuniversity.ac.ke'
        MY_SYSTEM_API_KEY  = 'your-api-key'
    """

    event         = 'payment.confirmed'
    model         = 'Payment'
    max_retries   = 5
    retry_backoff = 120   # seconds, doubles each retry

    def sync(self, instance) -> ERPSyncResult:
        """
        instance is a Payment object.
        Push it to the external ERP.
        Raise any exception on failure — the core will retry.
        """
        from django.conf import settings
        import requests

        response = requests.post(
            f"{settings.MY_SYSTEM_BASE_URL}/api/payments",
            json={
                'student_id':  str(instance.account.student.record_id),
                'amount':      str(instance.amount),
                'method':      instance.method,
                'reference':   instance.transaction_ref,
                'purpose':     instance.purpose,
            },
            headers={'X-API-Key': settings.MY_SYSTEM_API_KEY},
            timeout=30
        )

        if response.status_code in (200, 201):
            return ERPSyncResult(
                success=True,
                message='Synced to MySystem ERP',
                external_ref=response.json().get('ledger_id'),
                raw_response=response.json()
            )

        # returning success=False triggers a retry
        return ERPSyncResult(
            success=False,
            message=f"ERP returned {response.status_code}: {response.text}"
        )
```

### 3. Register it

```python
def ready(self):
    from erp.registry import erp_registry
    from contrib.erp.my_system import MySystemPaymentTask
    erp_registry.register(MySystemPaymentTask())
```

### Available events to listen to

```
payment.confirmed       enrollment.approved
payment.failed          enrollment.rejected
deferment.created       result.published
deferment.reinstated    reporting.submitted
student.graduated       student.registered
```

You can also listen to multiple events from one task:

```python
class MyTask(AbstractERPTask):
    event = ['payment.confirmed', 'payment.failed']
```

---

## 📡 Adding a Notification Backend

Notification backends deliver messages to users via a specific channel.

### 1. Create your backend file

```
contrib/notifications/my_provider.py
```

### 2. Implement `AbstractNotificationBackend`

```python
# contrib/notifications/my_provider.py

from notifications.backends.base import AbstractNotificationBackend


class MyProviderSMSBackend(AbstractNotificationBackend):
    """
    SMS backend via MyProvider.

    Configuration:
        MY_PROVIDER_SMS_KEY      = 'your-api-key'
        MY_PROVIDER_SENDER_ID    = 'MYUNI'
    """

    channel = 'sms'

    def send(self, user, template_key: str, context: dict) -> bool:
        """
        Render the template and send to the user.
        Return True on success, False on failure.
        Raise exceptions freely — the notification engine logs them.
        """
        from django.conf import settings
        from notifications.templates import render_template
        import requests

        message = render_template(template_key, 'sms', context)
        if not message:
            return False

        phone = self._get_phone(user)
        if not phone:
            return False

        response = requests.post(
            'https://api.myprovider.com/sms/send',
            json={
                'to':      phone,
                'message': message,
                'from':    settings.MY_PROVIDER_SENDER_ID,
            },
            headers={'Authorization': f"Bearer {settings.MY_PROVIDER_SMS_KEY}"},
            timeout=10
        )
        return response.status_code == 200

    def _get_phone(self, user) -> str | None:
        student = getattr(user, 'student_profile', None)
        return getattr(student, 'telephone_no', None)
```

### 3. Register it

```python
def ready(self):
    from notifications.registry import notification_registry
    from contrib.notifications.my_provider import MyProviderSMSBackend
    notification_registry.register(MyProviderSMSBackend())
```

---

## 📧 Adding an Email Strategy

Email strategies control how institutional email addresses are generated
from registration numbers.

```python
# contrib/email/my_strategy.py

def my_strategy(registration_number: str, domain: str) -> str:
    """
    Custom email generation strategy.

    e.g. 'ENG/001/2024' → 'eng.001.2024@myuniversity.ac.ke'
    """
    parts = registration_number.lower().split('/')
    local = '.'.join(parts)
    return f"{local}@{domain}"
```

Point to it in settings:

```python
SCHOOL_EMAIL_STRATEGY = 'contrib.email.my_strategy.my_strategy'
```

---

## 📅 Adding an Events Backend

The events module gives the portal a calendar — exam schedules, deadlines,
campus events, holidays — pulled from whatever source an institution
already uses. It follows the same open, pluggable architecture as payments
and ERP: a core contract, a registry, and contributor-supplied backends.

### Folder structure

```
events/
├── backends/
│   ├── contrib/          ← community backends go here
│   │   └── backends/
│   ├── __init__.py
│   └── base.py           ← AbstractEventsBackend + dataclasses
├── registry.py           ← events_registry
├── tasks.py              ← Celery beat — periodic fetch
├── urls.py                ← webhook routes
└── views.py               ← generic webhook receiver
```

### Where to write your backend

```
Local integrator / corporate setup
└── events/backends/your_backend.py        ← alongside base.py

Open source contributor
└── events/contrib/backends/your_backend.py ← keeps core clean
```

### 1. Implement `AbstractEventsBackend`

```python
# events/contrib/backends/google_calendar.py

from events.backends.base import (
    AbstractEventsBackend,
    EventFetchResult,
    EventWebhookResult,
)


class GoogleCalendarEventsBackend(AbstractEventsBackend):
    """
    Pulls events from a Google Calendar.

    Configuration:
        GOOGLE_CALENDAR_ID  = 'your-calendar-id@group.calendar.google.com'
        GOOGLE_CALENDAR_KEY = 'path/to/service-account.json'
    """

    source = 'google_calendar'

    def fetch(self) -> EventFetchResult:
        """
        Pull events from the external source.

        DO NOT write to the database here — return an EventFetchResult
        and let the core handle deduplication, storage, and logging.
        """
        ...

    def verify_webhook(self, request) -> EventWebhookResult:
        """
        Verify and parse an incoming push notification
        (e.g. Google Calendar push notifications on change).

        DO NOT write to the database here.
        """
        ...
```

### 2. Register it

**Static registration** (core, integrator, or contrib modules):

```python
# events/backends/__init__.py or apps.py

from events.registry import events_registry
from events.backends.google_calendar import GoogleCalendarEventsBackend
from events.contrib.backends.ical import ICalEventsBackend

events_registry.register(GoogleCalendarEventsBackend())
events_registry.register(ICalEventsBackend())
```

**Dynamic registration** (third-party isolated Django app):

```python
# outside_app/apps.py

from django.apps import AppConfig

class OutsideAppConfig(AppConfig):
    name = 'outside_app'

    def ready(self):
        from events.registry import events_registry
        from .backends import CustomCalendarBackend

        events_registry.register(CustomCalendarBackend())
```

### Execution flow contract

```
✅ fetch() and verify_webhook() return data structures only
✅ Never modify database records inside fetch() or verify_webhook()
✅ Always return EventFetchResult or EventWebhookResult
❌ Status calculation, RSVP cutoff tracking, ledger safety
   — handled by core, not your backend
```

### Checklist before submitting

```
✅ Implements AbstractEventsBackend
✅ source attribute set and unique
✅ fetch() never touches the database directly
✅ verify_webhook() never touches the database directly
✅ Settings documented in class docstring
✅ Example added to examples/events/
✅ Registered via one of the two patterns above
```

---

## 📰 Adding a News Backend

The news module pulls institutional announcements from external sources —
a WordPress blog, an RSS feed, a CMS — into the portal's news feed.
Same architecture, same contract.

### Folder structure

```
news/
├── backends/
│   ├── contrib/
│   │   └── backends/      ← community backends go here
│   ├── __init__.py
│   └── base.py            ← AbstractNewsBackend + dataclasses
├── registry.py            ← news_registry
├── tasks.py                ← Celery beat — periodic fetch
├── urls.py                 ← webhook routes
└── views.py                ← generic webhook receiver
```

### Where to write your backend

```
Local integrator / corporate setup
└── news/backends/your_backend.py         ← alongside base.py

Open source contributor
└── news/contrib/backends/your_backend.py  ← keeps core clean
```

### 1. Implement `AbstractNewsBackend`

```python
# news/contrib/backends/rss.py

from news.backends.base import (
    NewsArticle,
    NewsFetchResult,
    WebhookVerificationResult,
    AbstractNewsBackend,
)


class RSSNewsBackend(AbstractNewsBackend):
    """
    Pulls articles from an RSS feed.

    Configuration:
        RSS_FEED_URL = 'https://institution.ac.ke/news/feed/'
    """

    source = 'rss'

    def fetch(self) -> NewsFetchResult:
        """
        Pull articles from the feed.
        Return a NewsFetchResult containing NewsArticle items.

        DO NOT write to the database here — deduplication and
        storage are handled by core.
        """
        ...

    def verify_webhook(self, request) -> WebhookVerificationResult:
        """
        Verify and parse an incoming push (e.g. WordPress webhook
        on new post publish).

        DO NOT write to the database here.
        """
        ...
```

### 2. Register it

**Static registration:**

```python
# news/backends/__init__.py or apps.py

from news.registry import news_registry
from news.backends.wordpress import WordPressNewsBackend
from news.contrib.backends.rss import RSSNewsBackend

news_registry.register(WordPressNewsBackend())
news_registry.register(RSSNewsBackend())
```

**Dynamic registration** (third-party isolated Django app):

```python
# outside_app/apps.py

from django.apps import AppConfig

class OutsideAppConfig(AppConfig):
    name = 'outside_app'

    def ready(self):
        from news.registry import news_registry
        from .backends import CustomCMSBackend

        news_registry.register(CustomCMSBackend())
```

### Execution flow contract

```
✅ fetch() and verify_webhook() return data structures only
✅ Never modify database records inside fetch() or verify_webhook()
✅ Always return NewsFetchResult or WebhookVerificationResult
❌ Article deduplication, storage updates, sync logging
   — handled by core, not your backend
```

### Checklist before submitting

```
✅ Implements AbstractNewsBackend
✅ source attribute set and unique
✅ fetch() never touches the database directly
✅ verify_webhook() never touches the database directly
✅ Settings documented in class docstring
✅ Example added to examples/news/
✅ Registered via one of the two patterns above
```

---

## 🧪 Writing Tests

Tests are always welcome — especially for the financial logic which is
the most critical and most undertested part of the system.

### Where tests live

```
base/tests/
├── test_models.py       ← model properties, constraints, validation
├── test_signals.py      ← auto-enrollment, notifications
├── test_views.py        ← HTTP responses, redirects, context
├── test_admin.py        ← scoping, permissions, formfield filtering
└── test_payments.py     ← payment logic, overdraft, fee accounts
```

### What we need most

```
Priority
├── Payment.confirm() — normal, overpayment, cleared account
├── OverDraft.process() — carry-forward, refund
├── Student.expected_graduation_session — with and without deferments
├── auto_enroll_core_courses signal
└── ScopedAdminMixin.get_queryset() per role
```

### Running tests

```bash
python manage.py test
python manage.py test base.tests.test_payments   # specific file
python manage.py test --verbosity=2              # with output
```

### Test conventions

```python
class PaymentTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # read-only fixtures — built once for the class
        cls.session = Session.objects.create(...)

    def setUp(self):
        # per-test setup — rebuilt before each test
        self.account = StudentFeeAccount.objects.create(...)

    def test_normal_payment_updates_balance(self):
        # Arrange
        payment = Payment(account=self.account, amount=20000, ...)

        # Act
        payment.save()
        self.account.refresh_from_db()

        # Assert
        self.assertEqual(self.account.amount_paid, 20000)
```

---

## 📄 Writing Docs

Documentation lives in `docs/` and follows the structure in
[docs/README.md](docs/README.md).

### What to document when adding a backend

1. Add a row to the relevant table in `docs/extending/`
2. Document configuration (settings required)
3. Add a usage example

### What to document when adding a model or field

Update `docs/models.md` with the new field, its type, and any constraints.

### Diagrams

Diagrams use Mermaid and render automatically on GitHub.
Keep node labels emoji-free inside `mermaid` blocks — they cause parse errors.

---

## 🔀 Submitting a Pull Request

### Before you open a PR

```
✅ Tests pass             python manage.py test
✅ No new warnings        python manage.py check
✅ Migrations clean       python manage.py makemigrations --check
✅ Docs updated           if you added a model, view, or backend
✅ Example added          if you added a backend to contrib/
```

### PR title format

```
feat: add Flutterwave payment backend
fix: correct overdraft carry-forward logic
docs: add ERP task contributing guide
test: add payment confirmation tests
refactor: extract EmergencyContact model
```

### PR description

Tell us:

- What the PR does
- Why it's needed
- Any decisions you made that aren't obvious from the code
- What you tested

---

## 🎨 Code Style

```
Python version   3.10+
Formatter        black (recommended, not enforced yet)
Imports          isort
Line length      88 (black default)
```

Things we care about:

- Descriptive variable names — `student_fee_account` not `sfa`
- Docstrings on abstract methods — they're the contract
- No logic in views that belongs in services
- No hardcoded strings that should be settings
- `transaction.atomic()` on any write that touches multiple tables

Things we don't enforce (yet):

- Type hints — welcome but not required
- Strict linting — we're not there yet

---

## 🐛 Reporting Bugs

Open an issue with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Django version, Python version, database

For security vulnerabilities — **do not open a public issue**.

<!-- Email [security@yourdomain.com](mailto:security@yourdomain.com) directly. -->

---

## 💬 Questions

Open a Discussion on GitHub — not an Issue.
Issues are for bugs and concrete feature requests.
Discussions are for everything else.

---

## 📜 Licence

By contributing, you agree that your contributions will be licensed
under the Apache License 2.0 — the same licence as this project.

---

_Built with care in Kenya 🇰🇪 — contributions from anywhere welcome._
