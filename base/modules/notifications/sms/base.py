# base/modules/notifications/sms/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from base.modules.notifications.base import NotificationResult


@dataclass
class SMSPayload:
    to_number: str
    body:      str
    sender_id: Optional[str] = None


class AbstractSMSBackend(ABC):
    provider_name: str = ""

    @abstractmethod
    def send(self, payload: SMSPayload) -> NotificationResult:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True
