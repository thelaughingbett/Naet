"""
Notifications Backend Module & Registry System

This module implements an open, pluggable architecture for notification delivery.
Every notification provider must inherit from either `AbstractEmailBackend` or
`AbstractSMSBackend` and register its instance with the system's global
notification registry.


Folder Structure Reference:
base/modules/notifications/
├── __init__.py              # top-level init, exports all public symbols
├── base.py                  # NotificationResult only (shared result dataclass)
├── registry.py              # NotificationRegistry (unchanged)
├── templates.py             # NOTIFICATION_TEMPLATES, render_email, render_sms (unchanged)
├── service.py               # NotificationService (unchanged)
│
├── email/
│   ├── __init__.py          # email submodule init
│   ├── base.py              # EmailPayload + AbstractEmailBackend
│   └── backends/
│       ├── __init__.py
│       ├── examples/
│       │   └── backends.sendgrid.example.py
│       └── contrib/
│           └── __init__.py
│
└── sms/
    ├── __init__.py          # sms submodule init
    ├── base.py              # SMSPayload + AbstractSMSBackend
    └── backends/
        ├── __init__.py
        ├── africastalking.py        # moves here from backends/
        ├── messagepit.py            # SMS half moves here
        ├── examples/
        │   └── backends.africastalking.example.py
        └── contrib/
            └── __init__.py


Where to Write Your Custom Backend:

    1. Local Integrator / Corporate Setup:
       Write your provider module directly inside `backends/` alongside `base.py`.
       Typical for institution-specific providers or custom SMTP configurations.

    2. Open-Source Contributor Setup:
       Write your provider module inside `backends/contrib/backends/` to keep
       the core code footprint clean and maintainable.


Registration Patterns:

    Pattern A: Static Registration (Core / Integrator / Contributor Modules)
    -------------------------------------------------------------------------
    Import and register your backend instances explicitly inside the initialization
    sequence of your application startup hook, or directly in this init package:

        from base.modules.notifications.registry import notification_registry
        from base.modules.notifications.backends.africastalking import AfricasTalkingBackend
        from base.modules.notifications.backends.sendgrid import SendGridEmailBackend

        notification_registry.register_sms(AfricasTalkingBackend())
        notification_registry.register_email(SendGridEmailBackend())

    Pattern B: Dynamic Integration (Third-Party Isolated Django Apps)
    ------------------------------------------------------------------
    If your backend lives in a detached third-party module app, register it via
    Django's Application Configuration startup hook:

        # base/apps.py
        from django.apps import AppConfig

        class BaseConfig(AppConfig):
            name = 'base'

            def ready(self):
                from base.modules.notifications.registry import notification_registry
                from base.modules.notifications.backends.africastalking import AfricasTalkingBackend
                from base.modules.notifications.backends.sendgrid import SendGridEmailBackend

                notification_registry.register_sms(AfricasTalkingBackend())
                notification_registry.register_email(SendGridEmailBackend())

    Pattern C: Environment-Switching (Development vs Production)
    ------------------------------------------------------------
    Use Django's DEBUG flag to swap backends without changing call sites.
    All NotificationService.send() calls remain identical across environments:

        # base/apps.py
        def ready(self):
            from django.conf import settings
            from base.modules.notifications.registry import notification_registry

            if settings.DEBUG:
                from base.modules.notifications.backends.messagepit import (
                    MessagePitSMSBackend,
                    MessagePitEmailBackend,
                )
                notification_registry.register_sms(MessagePitSMSBackend())
                notification_registry.register_email(MessagePitEmailBackend())
            else:
                from base.modules.notifications.backends.africastalking import AfricasTalkingBackend
                from base.modules.notifications.backends.sendgrid import SendGridEmailBackend
                notification_registry.register_sms(AfricasTalkingBackend())
                notification_registry.register_email(SendGridEmailBackend())


Execution Flow Contract:
    - Custom backends must NEVER render templates inside send().
      Template rendering is handled exclusively by NotificationService via templates.py.
    - Always return standard NotificationResult — never raise exceptions out of send().
    - On failure, return NotificationResult(success=False, message=str(e)) and let
      the service layer handle logging and graceful degradation.
    - Financial side effects, ledger updates, and audit trails are handled upstream
      by the calling service — never inside a backend.


Unlike the payments registry which supports multiple active backends (one per
provider per transaction), the notification registry holds exactly one active
email backend and one active SMS backend at a time. The institution configures
these once at startup and every NotificationService.send() call uses them.
"""
