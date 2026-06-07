from django.apps import AppConfig


class BaseConfig(AppConfig):
    name = 'base'

    def ready(self):
        import base.utils.receivers
        from base.modules.payments.registry import registry

        # from base.modules.payments.backends import MpesaBackend
        # from base.modules.payments.backends import EquityBankBackend  # integrator add this

        # registry.register(MpesaBackend())
        # registry.register(EquityBankBackend())

        # from erp.registry import erp_registry
        # from erp.tasks.implementations.university_erp import (
        #     UniversityERPTask,
        #     HostelERPTask,
        #     RegistrationFeeTask,
        # )

        # erp_registry.register(UniversityERPTask())
        # erp_registry.register(HostelERPTask())
        # erp_registry.register(RegistrationFeeTask())
