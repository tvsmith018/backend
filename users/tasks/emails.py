from celery import shared_task
from common.services.email_service import EmailService
from common.services.idempotency import acquire_lock

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5)
def send_email(self, email, code):
    key = f"pwd-reset:{email}:{code}"

    if not acquire_lock(key):
        return "Duplicate task ignored"
    
    EmailService.send_html_email(
        subject="PASSWORD RESET ID",
        recipient_list=[email],
        template="emails/auth/passwordresetcode.html",
        context={"code": code},
    )
