from base.modules.notifications.emails.base import AbstractEmailBackend
from base.modules.notifications.sms.base import AbstractSMSBackend


class NotificationRegistry:
    """
    Holds the active email and SMS backends.
    Only one of each is active at a time — unlike payments,
    you don't pick a notification backend per message.
    The institution configures one email backend and one SMS backend
    and everything uses those.
    """

    _email_backend: AbstractEmailBackend = None
    _sms_backend:   AbstractSMSBackend = None

    @classmethod
    def register_email(cls, backend: AbstractEmailBackend):
        if not backend.provider_name:
            raise ValueError(
                f"{backend.__class__.__name__} must define a provider_name"
            )
        cls._email_backend = backend

    @classmethod
    def register_sms(cls, backend: AbstractSMSBackend):
        if not backend.provider_name:
            raise ValueError(
                f"{backend.__class__.__name__} must define a provider_name"
            )
        cls._sms_backend = backend

    @classmethod
    def get_email(cls) -> AbstractEmailBackend:
        if not cls._email_backend:
            raise RuntimeError(
                "No email backend registered. "
                "Call notification_registry.register_email(...) in AppConfig.ready()"
            )
        return cls._email_backend

    @classmethod
    def get_sms(cls) -> AbstractSMSBackend:
        if not cls._sms_backend:
            raise RuntimeError(
                "No SMS backend registered. "
                "Call notification_registry.register_sms(...) in AppConfig.ready()"
            )
        return cls._sms_backend

    @classmethod
    def has_email(cls) -> bool:
        return cls._email_backend is not None

    @classmethod
    def has_sms(cls) -> bool:
        return cls._sms_backend is not None


notification_registry = NotificationRegistry()
