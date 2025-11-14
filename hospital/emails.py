from django.conf import settings
from django.core.mail import send_mail


def build_confirmation_url(token: str) -> str:
    frontend = settings.FRONTEND_URL.rstrip('/')
    return f'{frontend}/email/confirm?token={token}'


def send_confirmation_email(confirmation):
    appointment = confirmation.appointment
    patient_name = appointment.patient.user.get_full_name()
    doctor_name = appointment.doctor.user.get_full_name()
    confirm_url = build_confirmation_url(confirmation.token)
    subject = 'Confirma tu cita'
    message = (
        f'Hola {patient_name},\n\n'
        f'Recibimos una nueva cita con {doctor_name} el {appointment.date} a las {appointment.start_time}.\n'
        f'Por favor confirma tu asistencia usando el siguiente enlace:\n{confirm_url}\n\n'
        'Si no solicitaste esta cita, ignora este mensaje.'
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [appointment.patient.user.email])
    confirmation.sent_at = appointment.created_at
    confirmation.save(update_fields=['sent_at'])
