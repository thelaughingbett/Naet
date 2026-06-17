# base/modules/notifications/email/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from base.modules.notifications.base import NotificationResult


@dataclass
class EmailPayload:
    to_address:   str
    subject:      str
    html_body:    str
    text_body:    str
    from_address: Optional[str] = None
    reply_to:     Optional[str] = None
    attachments:  list[dict] = field(default_factory=list)


class AbstractEmailBackend(ABC):
    provider_name: str = ""

    @abstractmethod
    def send(self, payload: EmailPayload) -> NotificationResult:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True
