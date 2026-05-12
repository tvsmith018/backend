from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

logger = get_task_logger(__name__)

@shared_task(name="users.tasks.maintenance.flush_expired_tokens")
def flush_expired_tokens():
    try:
        call_command("flushexpiredtokens")
        logger.info("Expired tokens flushed successfully.")
    except Exception as e:
        logger.error(f"Error flushing tokens: {e}")
