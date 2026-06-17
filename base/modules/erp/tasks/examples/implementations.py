
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
import requests
from django.conf import settings
from base.modules.erp.tasks.base import (
    AbstractERPTask,
    ERPSyncResult
)


class PaymentERPTask(AbstractERPTask):
    event = 'payment.confirmed'
    model = 'Payment'
    endpoint = 'https://erp.university.ac.ke/api/payments/'

    def sync(self, instance) -> ERPSyncResult:
        try:
            response = requests.post(
                self.get_endpoint(),           # → MessagePit in DEBUG
                json={
                    'ref':     instance.transaction_ref,
                    'amount':  str(instance.amount),
                    'student': instance.account.student.registration_number,
                },
                headers={'Authorization': f'Bearer {settings.ERP_API_KEY}'},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return ERPSyncResult(
                success=True,
                external_ref=data.get('id'),
                raw_response=data,
            )
        except Exception as e:
            return ERPSyncResult(success=False, message=str(e))


class EnrollmentERPTask(AbstractERPTask):
    event = 'enrollment.approved'
    model = 'Enrollment'
    endpoint = 'https://erp.university.ac.ke/api/enrollments/'

    def sync(self, instance) -> ERPSyncResult:
        try:
            response = requests.post(
                self.get_endpoint(),
                json={
                    'student':  instance.student.registration_number,
                    'units':    [u.code for u in instance.units.all()],
                    'session':  str(instance.session),
                },
                headers={'Authorization': f'Bearer {settings.ERP_API_KEY}'},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return ERPSyncResult(success=True, external_ref=data.get('id'), raw_response=data)
        except Exception as e:
            return ERPSyncResult(success=False, message=str(e))


class HELBReportingTask(AbstractERPTask):
    event = 'reporting.submitted'
    model = 'Reporting'
    endpoint = 'https://api.helb.go.ke/v1/reporting/'

    def sync(self, instance) -> ERPSyncResult:
        try:
            response = requests.post(
                self.get_endpoint(),
                json={
                    'national_id': instance.student.national_id,
                    'session':     str(instance.session),
                    'status':      'confirmed',
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return ERPSyncResult(success=True, external_ref=data.get('ref'), raw_response=data)
        except Exception as e:
            return ERPSyncResult(success=False, message=str(e))


class DefermentNotificationTask(AbstractERPTask):
    event = 'deferment.created'
    model = 'Deferment'
    endpoint = 'https://erp.university.ac.ke/api/deferments/'

    def sync(self, instance) -> ERPSyncResult:
        try:
            response = requests.post(
                self.get_endpoint(),
                json={
                    'student':       instance.student.registration_number,
                    'reason':        instance.reason,
                    'reason_detail': instance.reason_detail,
                    'from':          str(instance.session_deferred),
                    'to':            str(instance.session_returning) if instance.session_returning else None,
                    'status':        instance.status,
                    'approved_by':   str(instance.approved_by) if instance.approved_by else None,
                },
                timeout=10,
            )

            # don't raise_for_status before checking body —
            # some webhook receivers return 200 with empty body
            raw = response.text  # get raw text first

            # try to parse JSON — but don't crash if empty or HTML
            try:
                data = response.json() if raw.strip() else {}
            except ValueError:
                # store first 200 chars for debugging
                data = {'raw': raw[:200]}

            if response.ok:
                return ERPSyncResult(
                    success=True,
                    external_ref=str(data.get('id', 'received')),
                    raw_response=data,
                )

            return ERPSyncResult(
                success=False,
                message=f"HTTP {response.status_code}: {raw[:200]}",
                raw_response=data,
            )

        except requests.ConnectionError:
            return ERPSyncResult(success=False, message=f"Could not connect to {self.get_endpoint()}")
        except requests.Timeout:
            return ERPSyncResult(success=False, message="Request timed out")
        except Exception as e:
            return ERPSyncResult(success=False, message=str(e))


class FeeAccountCreatedTask(AbstractERPTask):
    event = 'feeaccount.created'
    model = 'StudentFeeAccount'
    endpoint = 'https://erp.university.ac.ke/api/finance/fee-accounts'

    def sync(self, instance):
        try:
            erp_api_key = getattr(settings, 'ERP_API_KEY', 'api-key-test')
            response = requests.post(
                self.get_endpoint(),
                json={
                    'student':          instance.student.registration_number,
                    'session':          str(instance.fee_structure.session),
                    'class':            str(instance.fee_structure.Tclass),
                    'amount_billed':    str(instance.amount_billed),
                    'breakdown':        instance.fee_structure.breakdown,  # already a dict — safe
                },
                headers={'Authorization': f'Bearer {erp_api_key}'},
                timeout=10,
            )

            # don't raise_for_status before checking body —
            # some webhook receivers return 200 with empty body
            raw = response.text  # get raw text first

            # try to parse JSON — but don't crash if empty or HTML
            try:
                data = response.json() if raw.strip() else {}
            except ValueError:
                # store first 200 chars for debugging
                data = {'raw': raw[:200]}

            if response.ok:
                return ERPSyncResult(
                    success=True,
                    external_ref=str(data.get('id', 'received')),
                    raw_response=data,
                )

            return ERPSyncResult(
                success=False,
                message=f"HTTP {response.status_code}: {raw[:200]}",
                raw_response=data,
            )

        except requests.ConnectionError:
            return ERPSyncResult(success=False, message=f"Could not connect to {self.get_endpoint()}")
        except requests.Timeout:
            return ERPSyncResult(success=False, message="Request timed out")
        except Exception as e:
            return ERPSyncResult(success=False, message=str(e))
