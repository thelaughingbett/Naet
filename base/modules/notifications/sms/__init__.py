"""
SMS Backend Submodule

This submodule defines the contract, payload, and backend implementations
for SMS delivery within the notification system.

Every SMS provider must inherit from `AbstractSMSBackend` defined in `sms/base.py`
and register its instance with the global `NotificationRegistry`.


Folder Structure Reference:
    base/modules/notifications/sms/
    ├── __init__.py          # This file
    ├── base.py              # SMSPayload + AbstractSMSBackend contract
    └── backends/
        ├── __init__.py
        ├── africastalking.py    # Africa's Talking (production — recommended for Kenya)
        ├── messagepit.py        # MessagePit (development — captures SMS locally)
        ├── examples/
        │   └── backends.africastalking.example.py
        └── contrib/
            └── __init__.py      # Community-contributed SMS backends


Payload:
    SMSPayload is the only object passed into every backend's send() method.
    It is built exclusively by NotificationService._send_sms() — backends
    never construct it themselves.

        SMSPayload(
            to_number = '+254712345678',   # E.164 format — required
            body      = 'Your OTP is ...' # plain text, ~160 chars per SMS
            sender_id = 'NAET-PORTAL',    # shortcode or alphanumeric — optional
        )


Available Backends:

    africastalking  →  sms/backends/africastalking.py
        Production SMS via Africa's Talking API.
        Recommended for Kenya and East Africa.
        Requires:
            AFRICASTALKING_USERNAME = 'your-username'
            AFRICASTALKING_API_KEY  = 'your-api-key'
            SMS_SENDER_ID           = 'NAET'   # optional shortcode

    messagepit  →  sms/backends/messagepit.py
        Development backend. Captures outgoing SMS in a local MessagePit
        instance instead of sending to real phones.
        SMS messages are visible at http://localhost:8025 (SMS tab).
        Requires messagepit.exe to be running locally.
        Optional settings:
            MESSAGEPIT_SMS_URL = 'http://localhost:8200'  # default


Registration:

    Register exactly one SMS backend at application startup.
    The registry rejects registration without a provider_name.

    Production:
        from base.modules.notifications.sms.backends.africastalking import AfricasTalkingBackend
        from base.modules.notifications.registry import notification_registry

        notification_registry.register_sms(AfricasTalkingBackend())

    Development:
        from base.modules.notifications.sms.backends.messagepit import MessagePitSMSBackend
        from base.modules.notifications.registry import notification_registry

        notification_registry.register_sms(MessagePitSMSBackend())

    Environment-switching (recommended pattern in apps.py):
        def ready(self):
            from django.conf import settings
            from base.modules.notifications.registry import notification_registry

            if settings.DEBUG:
                from base.modules.notifications.sms.backends.messagepit import MessagePitSMSBackend
                notification_registry.register_sms(MessagePitSMSBackend())
            else:
                from base.modules.notifications.sms.backends.africastalking import AfricasTalkingBackend
                notification_registry.register_sms(AfricasTalkingBackend())


Writing a Custom SMS Backend:

    Subclass AbstractSMSBackend, set provider_name, and implement send():

        from base.modules.notifications.sms.base import AbstractSMSBackend, SMSPayload
        from base.modules.notifications.base import NotificationResult

        class CustomSMSBackend(AbstractSMSBackend):
            provider_name = "custom_provider"

            def send(self, payload: SMSPayload) -> NotificationResult:
                try:
                    # call your provider's API here
                    return NotificationResult(success=True, message_id='...')
                except Exception as e:
                    return NotificationResult(success=False, message=str(e))

    Place local backends in  sms/backends/
    Place contributed backends in  sms/backends/contrib/


Execution Contract:
    - send() must never raise — catch all exceptions and return NotificationResult.
    - send() must never render templates — receive body via SMSPayload.body as-is.
    - send() must never write to the database — the service layer owns that.
    - Return NotificationResult(success=False, message=str(e)) on any failure.
"""
