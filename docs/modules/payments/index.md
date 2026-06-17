# 💳 Payments Module

> Everything about how money moves through Naet — how backends work,
> how to add a new payment provider, and how the system stays clean
> no matter which gateway an institution uses.
> Think of this as the contract between the gateway world and the ledger world.

---

## 🗺️ Overview

The payments system is **pluggable by design**. Naet doesn't care whether you
pay via M-Pesa, bank transfer, cash, or a gateway that doesn't exist yet.
Every provider is just an implementation of the same contract.

```
Student clicks "Pay"
      ↓
PaymentView creates a pending Payment record
      ↓
PaymentService.initiate() looks up the backend from the registry
      ↓
Backend fires the actual provider API (STK push, redirect, etc.)
      ↓
Provider calls back via webhook
      ↓
PaymentService.confirm() updates the ledger
      ↓
Student account balance updated — notification fired
```

The view and the ledger know nothing about M-Pesa.
The M-Pesa backend knows nothing about the ledger.
`PaymentService` is the only thing that knows both.

---

## 🏗️ Architecture

```
payments/
├── backends/
│   ├── __init__.py       # exports AbstractPaymentBackend + dataclasses
│   ├── base.py           # the contract — AbstractPaymentBackend, dataclasses
│   └── contrib/          # community-contributed backends go here
│       └── README.md
├── registry.py           # PaymentRegistry singleton
├── services.py           # PaymentService — orchestration + ledger logic
├── urls.py               # webhook routing
└── views.py              # PaymentConfigView, PaymentStatusView
```

---

## 📐 The Contract

Every backend must implement three methods. That's it.

```python
class AbstractPaymentBackend(ABC):

    method: str = ""  # must match Payment.PAYMENT_METHOD_CHOICES key

    @abstractmethod
    def initiate(self, payment, **kwargs) -> PaymentInitiationResult:
        """Fire the payment. Return what you know. Touch nothing in the DB."""
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, request) -> WebhookVerificationResult:
        """Parse + verify the provider's callback. Return the result. Touch nothing in the DB."""
        raise NotImplementedError

    @abstractmethod
    def get_form_config(self) -> PaymentFormConfig:
        """Describe what fields the payment modal should render for this backend."""
        raise NotImplementedError
```

### 📦 The dataclasses

| Dataclass                   | Returned by                | Purpose                                                         |
| --------------------------- | -------------------------- | --------------------------------------------------------------- |
| `PaymentInitiationResult`   | `initiate()`               | Did the provider accept the request? What ref did they give us? |
| `WebhookVerificationResult` | `verify_webhook()`         | Is this webhook legit? What's the confirmed transaction ref?    |
| `PaymentFormConfig`         | `get_form_config()`        | What should the modal render for this method?                   |
| `FormField`                 | inside `PaymentFormConfig` | A single input field definition                                 |

---

## 🔌 Flow types

Your backend declares its flow type in `get_form_config()`. The frontend modal
branches on this — so you don't write any frontend code for your backend.

| Flow       | What happens                                                 | Example                |
| ---------- | ------------------------------------------------------------ | ---------------------- |
| `stk_push` | Modal submits → JS polls `/pay/status/<id>/` until confirmed | M-Pesa                 |
| `redirect` | Modal submits → JS redirects to `result.redirect_url`        | Bank portal            |
| `manual`   | Modal submits → immediately confirmed                        | Cash at finance office |

---

## 🛠️ Adding a New Backend

### Step 1 — Create your backend file

If you're contributing to the community:

```
payments/backends/contrib/your_provider.py
```

If you're building for your own institution:

```
payments/backends/your_provider.py
```

### Step 2 — Implement the contract

```python
from base.modules.payments.backends import (
    AbstractPaymentBackend,
    PaymentInitiationResult,
    WebhookVerificationResult,
    PaymentFormConfig,
    FormField,
)


class EquityBankBackend(AbstractPaymentBackend):

    method = 'bank'   # must match a Payment.PAYMENT_METHOD_CHOICES key

    def get_form_config(self) -> PaymentFormConfig:
        return PaymentFormConfig(
            method="bank",
            label="Pay via Equity Bank",
            icon="🏦",
            flow="redirect",
            instructions="You will be redirected to Equity Bank's secure payment portal.",
            fields=[
                FormField(
                    name="account_number",
                    label="Account Number",
                    type="text",
                    placeholder="000XXXXXXXX",
                )
            ]
        )

    def initiate(self, payment, **kwargs) -> PaymentInitiationResult:
        # call Equity's API here
        # DO NOT update payment or any model here
        response = call_equity_api(payment.amount, payment.account.student.registration_number)

        if response.ok:
            return PaymentInitiationResult(
                success=True,
                redirect_url=response.payment_url,
                provider_ref=response.transaction_id,
                message="Redirecting to Equity Bank...",
                raw_response=response.json(),
            )

        return PaymentInitiationResult(
            success=False,
            message=response.error_message,
            raw_response=response.json(),
        )

    def verify_webhook(self, request) -> WebhookVerificationResult:
        # verify the signature, parse the payload
        # DO NOT update any model here
        try:
            payload = json.loads(request.body)
            if not verify_signature(payload, request.headers.get('X-Equity-Signature')):
                return WebhookVerificationResult(valid=False, message="Invalid signature")

            return WebhookVerificationResult(
                valid=True,
                transaction_ref=payload['receipt_number'],
                provider_ref=payload['transaction_id'],
                amount=float(payload['amount']),
                raw_payload=payload,
            )
        except Exception as e:
            return WebhookVerificationResult(valid=False, message=str(e))
```

### Step 3 — Register it

```python
# base/apps.py
class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        from base.modules.payments.registry import registry
        from base.modules.payments.backends.your_provider import EquityBankBackend

        registry.register(EquityBankBackend())
```

That's it. The modal picks it up automatically via `/pay/config/`.
The webhook route is auto-registered as `/pay/webhook/bank/`.

---

## 🚦 The Golden Rules

> These are non-negotiable. Breaking them breaks the audit trail.

**1. Never touch the DB inside `initiate()` or `verify_webhook()`**
`PaymentService` owns the ledger. Your backend owns the provider conversation.
These two things must never mix.

**2. Always return a result dataclass — never raise**
Catch your exceptions internally. Return `success=False` with a message.
The service layer handles retries and notifications.

**3. `method` must match `Payment.PAYMENT_METHOD_CHOICES`**
If your method string doesn't exist in the choices, the Payment record
can't be created. Add your method to the model choices before registering.

**4. `provider_ref` in `PaymentInitiationResult` must match `provider_ref` in `WebhookVerificationResult`**
This is how the system matches the callback to the pending payment.
If these don't match, the webhook handler can't find the payment to confirm.

---

## 🧪 Testing your backend

```python
# tests/test_your_backend.py
from django.test import TestCase, RequestFactory
from unittest.mock import patch
from base.modules.payments.backends.your_provider import EquityBankBackend

class EquityBankBackendTest(TestCase):

    def setUp(self):
        self.backend = EquityBankBackend()

    def test_get_form_config(self):
        config = self.backend.get_form_config()
        self.assertEqual(config.method, 'bank')
        self.assertEqual(config.flow, 'redirect')
        self.assertTrue(len(config.fields) > 0)

    @patch('base.modules.payments.backends.your_provider.call_equity_api')
    def test_initiate_success(self, mock_api):
        mock_api.return_value.ok = True
        mock_api.return_value.payment_url = 'https://equity.co.ke/pay/123'
        mock_api.return_value.transaction_id = 'EQT123'
        mock_api.return_value.json.return_value = {}

        result = self.backend.initiate(mock_payment)
        self.assertTrue(result.success)
        self.assertEqual(result.redirect_url, 'https://equity.co.ke/pay/123')

    @patch('base.modules.payments.backends.your_provider.call_equity_api')
    def test_initiate_failure(self, mock_api):
        mock_api.return_value.ok = False
        mock_api.return_value.error_message = 'Service unavailable'
        mock_api.return_value.json.return_value = {}

        result = self.backend.initiate(mock_payment)
        self.assertFalse(result.success)
        self.assertIn('unavailable', result.message)

    def test_verify_webhook_invalid_signature(self):
        factory = RequestFactory()
        request = factory.post('/webhook/', data=b'{}', content_type='application/json')
        result = self.backend.verify_webhook(request)
        self.assertFalse(result.valid)
```

---

## 🔗 Where to Go Next

| Topic                      | Document                         |
| -------------------------- | -------------------------------- |
| 💰 Fee ledger logic        | [Fees Module](fees/index.md)     |
| 🔄 How webhooks are routed | `payments/urls.py`               |
| 🧾 Payment model fields    | [Models Reference](../models.md) |
| 📋 Registry pattern        | `payments/registry.py`           |
