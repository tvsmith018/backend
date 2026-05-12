from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

class EmailService:

    @staticmethod
    def send_html_email(*, subject, recipient_list, template, context):
        html_content = render_to_string(template, context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.EMAIL_HOST_USER,
            recipient_list,
        )

        msg.attach_alternative(html_content, "text/html")
        msg.send()
