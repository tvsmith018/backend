from celery import shared_task

@shared_task(
    name="users.cleanup_orphan_data.v1",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 1},
)
def cleanup_orphan_data():
    # destructive logic here
    pass
