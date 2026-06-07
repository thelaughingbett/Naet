# erp/tasks/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class ERPSyncResult:
    success:      bool
    message:      str = ""
    external_ref: Optional[str] = None
    raw_response: Optional[dict] = None


class AbstractERPTask(ABC):
    """
    Contract for any data that needs to be pushed to an external ERP.

    Not scoped to payments — any model can have a task.
    The task receives the instance, decides what to do with it,
    and returns an ERPSyncResult.

    Examples:
        PaymentERPTask       — sync confirmed payments to finance ledger
        EnrollmentERPTask    — push enrollment records to student registry
        DefermentERPTask     — notify HR/registry of student deferment
        ResultERPTask        — push results to academic records system
        ReportingERPTask     — confirm semester check-in to HELB

    Usage:
        class MyPaymentTask(AbstractERPTask):
            event    = 'payment.confirmed'
            model    = 'Payment'
            max_retries = 5

            def sync(self, instance) -> ERPSyncResult:
                # instance is a Payment object
                ...
    """

    # what triggered this sync — e.g. 'payment.confirmed', 'enrollment.approved'
    # used for routing and logging
    event: str = ""

    # the model this task handles — for logging and admin display
    model: str = ""

    # retry config
    max_retries:     int = 5
    retry_backoff:   int = 60
    retry_max_delay: int = 3600

    @abstractmethod
    def sync(self, instance: Any) -> ERPSyncResult:
        """
        Push this instance to the external ERP system.

        instance is the model object that triggered the sync —
        Payment, Enrollment, Deferment, Result, or anything else.

        Raise any exception on failure.
        Return ERPSyncResult(success=False) for soft failures.
        The core handles retries either way.
        """
        raise NotImplementedError

    def get_instance_ref(self, instance: Any) -> str:
        """
        Returns a human-readable reference for logging.
        Override if the default isn't descriptive enough.
        """
        return str(getattr(instance, 'record_id', instance))
