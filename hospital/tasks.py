from celery import shared_task
from django.utils import timezone

from .emails import send_confirmation_email
from .models import EmailConfirmation


@shared_task
def send_confirmation_email_task(confirmation_id: int):
    confirmation = EmailConfirmation.objects.select_related('appointment', 'appointment__patient__user').get(
        id=confirmation_id
    )
    send_confirmation_email(confirmation)
    confirmation.sent_at = timezone.now()
    confirmation.save(update_fields=['sent_at'])
