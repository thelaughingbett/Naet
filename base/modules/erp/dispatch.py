from django.db import transaction
from .tasks.sync import erp_sync


def dispatch_erp_event(instance, event: str):
    """
    Fire an ERP sync for any model instance.
    Safe to call from signals, views, or services.

    Usage:
        dispatch_erp_event(payment, 'payment.confirmed')
        dispatch_erp_event(enrollment, 'enrollment.approved')
        dispatch_erp_event(deferment, 'deferment.created')
        dispatch_erp_event(result, 'result.published')
    """
    app_label = instance.__class__._meta.app_label
    model_name = instance.__class__.__name__
    instance_id = str(instance.pk)

    transaction.on_commit(lambda: erp_sync.delay(
        app_label=app_label,
        model_name=model_name,
        instance_id=instance_id,
        event=event
    ))
