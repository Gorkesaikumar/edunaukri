from celery import shared_task
from apps.core.tasks import BaseTask
from apps.core.utils.locking import redis_lock


from apps.invoices.services.invoice_lifecycle_service import InvoiceLifecycleService


@shared_task(
    base=BaseTask,
    name="invoices.mark_overdue",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
@redis_lock("mark_overdue_invoices")
def mark_overdue_invoices_task(self, batch_size: int = 100) -> int:
    try:
        return InvoiceLifecycleService().mark_all_overdue(limit=batch_size)
    except Exception as exc:
        raise self.retry(exc=exc)
