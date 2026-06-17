# base/modules/notifications/base.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationResult:
    success:      bool
    message_id:   Optional[str] = None
    message:      str = ""
    raw_response: Optional[dict] = None
