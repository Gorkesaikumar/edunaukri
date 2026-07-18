import logging
import time
from celery import Task
from django.conf import settings

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """
    Base celery task providing standardized logging, timing, and error handling.
    """
    abstract = True

    def __call__(self, *args, **kwargs):
        self.start_time = time.time()
        return super().__call__(*args, **kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        duration = time.time() - getattr(self, 'start_time', time.time())
        logger.info(
            f"Task {self.name} [{task_id}] succeeded in {duration:.2f}s."
        )
        super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        duration = time.time() - getattr(self, 'start_time', time.time())
        logger.error(
            f"Task {self.name} [{task_id}] failed after {duration:.2f}s. "
            f"Error: {str(exc)}\n{einfo}"
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            f"Task {self.name} [{task_id}] retrying. Reason: {str(exc)}"
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)
