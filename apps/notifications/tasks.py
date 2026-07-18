from celery import shared_task
from apps.core.tasks import BaseTask
from apps.core.utils.locking import redis_lock


from apps.notifications.services.outbox_processor import OutboxProcessorService


@shared_task(
    base=BaseTask,
    name="notifications.process_outbox",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
@redis_lock("process_outbox")
def process_outbox_task(self, batch_size: int = 50) -> int:
    try:
        return OutboxProcessorService().process_batch(limit=batch_size)
    except Exception as exc:
        raise self.retry(exc=exc)
