import requests
from django.conf import settings
from erp.tasks.base import (
    AbstractERPTask,
    ERPSyncResult
)


"""
University ERP Integration Blueprints & Implementation Examples

This module serves as the authoritative implementation guide and template repository 
for university-specific ERP sync workflows. It contains reference handlers for core 
academic, financial, and regulatory pipelines.

Directory Placement:
    Save production implementations under: erp/tasks/examples/implementations.py
    Or within specialized modules under: erp/tasks/

Core Event Naming Convention:
    Always apply the structured 'model.action' pattern consistently across the platform:
    - Financial:   'payment.confirmed', 'payment.failed'
    - Academic:    'enrollment.approved', 'enrollment.rejected', 'result.published'
    - Lifecycle:   'deferment.created', 'deferment.reinstated', 'student.graduated'
    - Regulatory:  'reporting.submitted'

System Registration Hook:
    To activate these handlers, initialize and bind them within your application 
    configuration lifecycle startup method (`apps.py`):

        # base/apps.py
        from django.apps import AppConfig

        class BaseConfig(AppConfig):
            name = 'base'

            def ready(self):
                from erp.registry import erp_registry
                from erp.tasks.examples.implementations import (
                    PaymentERPTask,
                    EnrollmentERPTask,
                    HELBReportingTask,
                    DefermentNotificationTask,
                )
                
                # Bind handlers to the global event dispatcher pipeline
                erp_registry.register(PaymentERPTask())
                erp_registry.register(EnrollmentERPTask())
                erp_registry.register(HELBReportingTask())
                erp_registry.register(DefermentNotificationTask())

Execution Contract Safeguards:
    - Keep implementations side-effect free. Do not modify local DB state here.
    - Wrap all external network footprints safely within HTTP timeout boundaries.
    - Leverage `ERPSyncResult` payload envelopes to communicate delivery updates cleanly.
"""


class PaymentERPTask(AbstractERPTask):
    event = 'payment.confirmed'
    model = 'Payment'

    def sync(self, instance) -> ERPSyncResult:
        # instance is a Payment
        ...


class EnrollmentERPTask(AbstractERPTask):
    event = 'enrollment.approved'
    model = 'Enrollment'

    def sync(self, instance) -> ERPSyncResult:
        # instance is an Enrollment
        ...


class HELBReportingTask(AbstractERPTask):
    event = 'reporting.submitted'
    model = 'Reporting'

    def sync(self, instance) -> ERPSyncResult:
        # push semester check-in to HELB verification API
        ...


class DefermentNotificationTask(AbstractERPTask):
    event = 'deferment.created'
    model = 'Deferment'

    def sync(self, instance) -> ERPSyncResult:
        # notify HR system of student deferment
        ...
