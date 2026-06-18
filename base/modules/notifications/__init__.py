
"""
Notifications Module
 
The single outbound communication layer for the portal. Every email and SMS
the system sends — payment confirmations, result alerts, fee reminders,
enrollment approvals — flows through here. Nothing else in the codebase
talks directly to a mail server or SMS gateway.
 
The design is deliberately boring: one email backend, one SMS backend, both
swappable without touching call sites. In development you point both at
MessagePit and every message lands in a local inbox. In production you swap
to SendGrid and Africa's Talking. The rest of the codebase never knows the
difference.
 
───────────────────────────────────────────────────────────────────────────────
Architecture
───────────────────────────────────────────────────────────────────────────────
 
    Something happens (payment confirmed, results published, deferment filed…)
          │
          ▼
    NotificationService.send(user, template_key, channels, context)
          │
          ├─── email ──► render_email(template_key, context)
          │                    └─► AbstractEmailBackend.send(EmailPayload)
          │
          └─── sms ────► render_sms(template_key, context)
                               └─► AbstractSMSBackend.send(SMSPayload)
 
Template rendering is done by the service before the backend is called.
Backends receive fully-rendered strings — they never touch templates.
Backends never raise — they catch all exceptions and return NotificationResult.
 
───────────────────────────────────────────────────────────────────────────────
Folder Structure
───────────────────────────────────────────────────────────────────────────────
 
    base/modules/notifications/
    ├── __init__.py              ← this file; top-level public exports
    ├── base.py                  ← NotificationResult dataclass (shared)
    ├── registry.py              ← NotificationRegistry singleton
    ├── templates.py             ← NOTIFICATION_TEMPLATES, render_email, render_sms
    ├── service.py               ← NotificationService — the only public call site
    │
    ├── email/
    │   ├── __init__.py
    │   ├── base.py              ← EmailPayload + AbstractEmailBackend
    │   └── backends/
    │       ├── __init__.py
    │       ├── messagepit.py    ← dev: SMTP capture via MessagePit (port 1025)
    │       ├── examples/
    │       │   └── backends.sendgrid.example.py
    │       └── contrib/         ← community-contributed email backends
    │           └── __init__.py
    │
    └── sms/
        ├── __init__.py
        ├── base.py              ← SMSPayload + AbstractSMSBackend
        └── backends/
            ├── __init__.py
            ├── africastalking.py ← prod: Africa's Talking (recommended for Kenya)
            ├── messagepit.py     ← dev: Twilio-compatible capture (port 8200)
            ├── examples/
            │   └── backends.africastalking.example.py
            └── contrib/          ← community-contributed SMS backends
                └── __init__.py
 
───────────────────────────────────────────────────────────────────────────────
Sending a Notification
───────────────────────────────────────────────────────────────────────────────
 
    from base.modules.notifications.service import NotificationService
 
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
 
NotificationService.send() never raises. A missing backend, a failed
delivery, or a bad template key is logged and skipped — it never
propagates up to the caller. A failure on one channel does not affect
the other.
 
───────────────────────────────────────────────────────────────────────────────
Available Templates
───────────────────────────────────────────────────────────────────────────────
 
    Key                     Channels        Context keys required
    ─────────────────────── ─────────────── ─────────────────────────────────
    payment_confirmed       email + sms     amount, ref, balance
    payment_failed          email + sms     amount
    results_published       email + sms     session
    reporting_confirmed     email + sms     session, student_name
    fee_reminder            email + sms     balance, due_date
    enrollment_approved     email + sms     session
    registration_success    email + sms     (none required beyond user)
 
Templates live in NOTIFICATION_TEMPLATES in templates.py.
Email templates reference Django template files under
base/notifications/email/; SMS templates are inline format strings.
To add a template, add its entry to NOTIFICATION_TEMPLATES — no other
changes needed.
 
───────────────────────────────────────────────────────────────────────────────
Registry & Backend Registration
───────────────────────────────────────────────────────────────────────────────
 
The registry holds exactly one email backend and one SMS backend at a time.
Register both in AppConfig.ready() — never at import time.
 
    Pattern A — environment switching (recommended):
 
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
 
    Pattern B — static (single environment):
 
        notification_registry.register_email(SendGridEmailBackend())
        notification_registry.register_sms(AfricasTalkingBackend())
 
───────────────────────────────────────────────────────────────────────────────
Writing a Custom Backend
───────────────────────────────────────────────────────────────────────────────
 
    Email:
 
        from base.modules.notifications.email.base import AbstractEmailBackend, EmailPayload
        from base.modules.notifications.base import NotificationResult
 
        class MyEmailBackend(AbstractEmailBackend):
            provider_name = "my_provider"   # required — registry rejects blank
 
            def send(self, payload: EmailPayload) -> NotificationResult:
                try:
                    # call your provider API
                    return NotificationResult(success=True, message_id="...")
                except Exception as e:
                    return NotificationResult(success=False, message=str(e))
 
    SMS:
 
        from base.modules.notifications.sms.base import AbstractSMSBackend, SMSPayload
        from base.modules.notifications.base import NotificationResult
 
        class MySMSBackend(AbstractSMSBackend):
            provider_name = "my_sms_provider"
 
            def send(self, payload: SMSPayload) -> NotificationResult:
                try:
                    # call your provider API
                    return NotificationResult(success=True, message_id="...")
                except Exception as e:
                    return NotificationResult(success=False, message=str(e))
 
    Place institution-specific backends directly under email/backends/ or
    sms/backends/. Place reusable community backends under the contrib/
    subfolder of either.
 
───────────────────────────────────────────────────────────────────────────────
Local Development — MessagePit
───────────────────────────────────────────────────────────────────────────────
 
With DEBUG=True and MessagePit running locally:
 
    Email  →  http://localhost:8025  (Inbox tab)   SMTP port 1025
    SMS    →  http://localhost:8025  (SMS tab)      HTTP port 8200
 
No real emails or texts are sent. Every outbound message is captured and
visible in the MessagePit UI. The payloads are identical to what production
would send, so you can verify rendering and content before deploying.
 
    Optional settings (defaults shown):
        MESSAGEPIT_SMTP_HOST = 'localhost'
        MESSAGEPIT_SMTP_PORT = 1025
        MESSAGEPIT_SMS_URL   = 'http://localhost:8200'
 
───────────────────────────────────────────────────────────────────────────────
Execution Contract (mandatory for all backends)
───────────────────────────────────────────────────────────────────────────────
 
    ✗  Never raise out of send() — catch all exceptions, return NotificationResult.
    ✗  Never render templates inside send() — receive rendered strings via payload.
    ✗  Never write to the database — the service layer owns audit trails.
    ✓  Always return NotificationResult(success=False, message=str(e)) on failure.
    ✓  Set provider_name — the registry rejects backends without one.
 
───────────────────────────────────────────────────────────────────────────────
Public Exports
───────────────────────────────────────────────────────────────────────────────
"""

from base.modules.notifications.service import NotificationService
from base.modules.notifications.base import NotificationResult
from base.modules.notifications.registry import notification_registry

__all__ = [
    "NotificationService",
    "NotificationResult",
    "notification_registry",
]
