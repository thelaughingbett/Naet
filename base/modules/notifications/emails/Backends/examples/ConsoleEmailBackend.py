# base/modules/notifications/backends/console.py
# Development backends — print instead of sending

from base.modules.notifications.base import (
    NotificationResult
)

from base.modules.notifications.emails.base import (
    AbstractEmailBackend, EmailPayload
)


class ConsoleEmailBackend(AbstractEmailBackend):
    """Prints emails to the console. Use in development."""
    provider_name = "console-email"

    def send(self, payload: EmailPayload) -> NotificationResult:
        print(f"\n{'='*60}")
        print(f"📧  EMAIL")
        print(f"To:      {payload.to_address}")
        print(f"Subject: {payload.subject}")
        print(f"Body:    {payload.text_body[:200]}...")
        print(f"{'='*60}\n")
        return NotificationResult(success=True, message_id="console-dev", message="Printed to console")
