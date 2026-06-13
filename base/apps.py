from django.apps import AppConfig


class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        import base.utils.receivers
        from base.modules.payments.registry import registry

        from base.modules.payments.backends.examples.backends_mpesa_example import MpesaBackend
        from base.modules.payments.backends.examples.backends_equity_example import EquityBankBackend

        registry.register(MpesaBackend())
        registry.register(EquityBankBackend())
