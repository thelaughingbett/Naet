# base/modules/notifications/backends/console.py
# Development backends — print instead of sending

from base.modules.notifications.base import (
    NotificationResult
)

from base.modules.notifications.sms.base import (
    AbstractSMSBackend, SMSPayload
)


class ConsoleSMSBackend(AbstractSMSBackend):
    """Prints SMS to the console. Use in development."""
    provider_name = "console-sms"

    def send(self, payload: SMSPayload) -> NotificationResult:
        print(f"\n{'='*60}")
        print(f"📱  SMS")
        print(f"To:   {payload.to_number}")
        print(f"Body: {payload.body}")
        print(f"{'='*60}\n")
        return NotificationResult(success=True, message_id="console-dev", message="Printed to console")
