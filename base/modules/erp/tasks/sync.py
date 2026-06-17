import logging
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.apps import apps

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='erp.sync')
def erp_sync(self, app_label: str, model_name: str, instance_id: str, event: str):
    """
    Generic ERP sync task.
    Works for any model — Payment, Enrollment, Deferment, Result, anything.

    Args:
        app_label:   Django app label e.g. 'base'
        model_name:  Model class name e.g. 'Payment'
        instance_id: Primary key of the instance
        event:       Event string e.g. 'payment.confirmed'
    """
    from base.modules.erp.registry import erp_registry
    from base.modules.erp.models import ERPSyncLog

    logger.info(
        f"[erp_sync] fired — event={event} model={model_name} id={instance_id}"
    )

    # resolve the model and instance dynamically
    try:
        Model = apps.get_model(app_label, model_name)
        instance = Model.objects.get(pk=instance_id)
    except Exception as e:
        logger.error(
            f"[ERP] Could not load {app_label}.{model_name}:{instance_id} — {e}")
        return

    # get all handlers for this event
    handlers = erp_registry.get(event)
    if not handlers:
        logger.debug(f"[ERP] No handlers for event '{event}' — skipping")
        return

    # run each handler separately — each gets its own retry cycle
    for handler in handlers:
        _run_handler(self, handler, instance, event)


def _run_handler(task, handler, instance, event):
    from base.modules.erp.models import ERPSyncLog

    log = ERPSyncLog.objects.create(
        content_type_str=f"{instance.__class__.__name__}:{instance.pk}",
        event=event,
        handler=handler.__class__.__name__,
        attempt=task.request.retries + 1,
        status='attempting'
    )

    try:
        result = handler.sync(instance)

        if result.success:
            log.status = 'success'
            log.message = result.message
            log.external_ref = result.external_ref
            log.raw_response = result.raw_response or {}
            log.save()
        else:
            log.status = 'failed'
            log.message = result.message
            log.save()
            raise Exception(result.message)

    except Exception as exc:
        log.status = 'error'
        log.message = str(exc)
        log.save()

        delay = min(
            handler.retry_backoff * (2 ** task.request.retries),
            handler.retry_max_delay
        )

        logger.warning(
            f"[ERP] {handler.__class__.__name__} failed for "
            f"{instance.__class__.__name__}:{instance.pk} "
            f"(attempt {task.request.retries + 1}/{handler.max_retries}) "
            f"— retrying in {delay}s"
        )

        try:
            raise task.retry(
                exc=exc,
                countdown=delay,
                max_retries=handler.max_retries
            )
        except MaxRetriesExceededError:
            log.status = 'exhausted'
            log.message = f"Max retries exceeded. Last error: {exc}"
            log.save()
            logger.error(
                f"[ERP] Gave up on {handler.__class__.__name__} "
                f"for {instance.__class__.__name__}:{instance.pk}"
            )
