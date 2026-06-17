from django.apps import AppConfig
from django.conf import settings


class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        import base.utils.receivers

        from base.modules.payments.registry import registry
        from base.modules.payments.backends.examples.backends_mpesa_example import MpesaBackend
        from base.modules.payments.backends.examples.backends_equity_example import EquityBankBackend

        registry.register(MpesaBackend())
        registry.register(EquityBankBackend())

        if settings.DEBUG:
            from base.modules.erp.tasks.examples.implementations import DefermentNotificationTask, FeeAccountCreatedTask
            from base.modules.erp.registry import erp_registry

            erp_registry.register(DefermentNotificationTask())
            erp_registry.register(FeeAccountCreatedTask())

            from base.modules.notifications.registry import notification_registry
            from base.modules.notifications.emails.Backends.examples.MessagepitEmailBackend import MessagePitEmailBackend
            from base.modules.notifications.sms.Backends.examples.MessagePitBackend import MessagePitSMSBackend

            notification_registry.register_email(MessagePitEmailBackend())
            notification_registry.register_sms(MessagePitSMSBackend())
