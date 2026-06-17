"""
Email Backend Submodule

This submodule defines the contract, payload, and backend implementations
for email delivery within the notification system.

Every email provider must inherit from `AbstractEmailBackend` defined in `email/base.py`
and register its instance with the global `NotificationRegistry`.


Folder Structure Reference:
    base/modules/notifications/email/
    ├── __init__.py          # This file
    ├── base.py              # EmailPayload + AbstractEmailBackend contract
    └── backends/
        ├── __init__.py
        ├── messagepit.py        # MessagePit (development — captures email locally)
        ├── examples/
        │   └── backends.sendgrid.example.py
        └── contrib/
            └── __init__.py      # Community-contributed email backends


Payload:
    EmailPayload is the only object passed into every backend's send() method.
    It is built exclusively by NotificationService._send_email() — backends
    never construct it themselves. Subject, HTML body, and plain-text body
    are fully rendered before reaching the backend.

        EmailPayload(
            to_address   = 'student@example.com',   # required
            subject      = 'Payment Confirmed',      # pre-rendered — no templating here
            html_body    = '<p>...</p>',             # pre-rendered HTML
            text_body    = 'Plain text fallback',    # always required alongside HTML
            from_address = 'noreply@naet.ac.ke',    # falls back to DEFAULT_FROM_EMAIL
            reply_to     = None,                     # optional
            attachments  = [],                       # [{"filename": ..., "content": ..., "mimetype": ...}]
        )


Available Backends:

    messagepit  →  email/backends/messagepit.py
        Development backend. Delivers outgoing email to a local MessagePit
        SMTP server (port 1025) instead of a real mail provider.
        Emails are visible at http://localhost:8025 (Inbox tab).
        Requires messagepit.exe to be running locally.
        Optional settings:
            MESSAGEPIT_SMTP_HOST = 'localhost'   # default
            MESSAGEPIT_SMTP_PORT = 1025          # default

    (Production backends such as SendGrid or Mailgun go in email/backends/
     or email/backends/contrib/ — see Writing a Custom Email Backend below.)


Registration:

    Register exactly one email backend at application startup.
    The registry rejects registration without a provider_name.

    Production (e.g. SendGrid):
        from base.modules.notifications.email.backends.sendgrid import SendGridEmailBackend
        from base.modules.notifications.registry import notification_registry

        notification_registry.register_email(SendGridEmailBackend())

    Development:
        from base.modules.notifications.email.backends.messagepit import MessagePitEmailBackend
        from base.modules.notifications.registry import notification_registry

        notification_registry.register_email(MessagePitEmailBackend())

    Environment-switching (recommended pattern in apps.py):
        def ready(self):
            from django.conf import settings
            from base.modules.notifications.registry import notification_registry

            if settings.DEBUG:
                from base.modules.notifications.email.backends.messagepit import MessagePitEmailBackend
                notification_registry.register_email(MessagePitEmailBackend())
            else:
                from base.modules.notifications.email.backends.sendgrid import SendGridEmailBackend
                notification_registry.register_email(SendGridEmailBackend())


Writing a Custom Email Backend:

    Subclass AbstractEmailBackend, set provider_name, and implement send():

        from base.modules.notifications.email.base import AbstractEmailBackend, EmailPayload
        from base.modules.notifications.base import NotificationResult

        class CustomEmailBackend(AbstractEmailBackend):
            provider_name = "custom_provider"

            def send(self, payload: EmailPayload) -> NotificationResult:
                try:
                    # call your provider's API here
                    return NotificationResult(success=True, message_id='...')
                except Exception as e:
                    return NotificationResult(success=False, message=str(e))

    Place local backends in  email/backends/
    Place contributed backends in  email/backends/contrib/


Execution Contract:
    - send() must never raise — catch all exceptions and return NotificationResult.
    - send() must never render templates — receive subject, html_body, and text_body
      via EmailPayload as fully rendered strings.
    - send() must never write to the database — the service layer owns that.
    - Always send both html_body and text_body — never HTML-only.
    - Return NotificationResult(success=False, message=str(e)) on any failure.
"""
