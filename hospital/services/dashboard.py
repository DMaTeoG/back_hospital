from datetime import date

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from ..models import Appointment, Doctor, Patient, User


def _format_monthly(series):
    return [
        {'month': item['month'].strftime('%Y-%m'), 'count': item['count']}
        for item in series
    ]


def _empty_metrics():
    return {
        'kpis': [],
        'appointmentsBySpecialty': [],
        'newPatientsByMonth': [],
        'todayAppointments': [],
    }


def _map_appointment(appointment):
    patient_name = appointment.patient.user.get_full_name() if appointment.patient_id else ''
    doctor_name = appointment.doctor.user.get_full_name() if appointment.doctor_id else ''
    return {
        'id': appointment.id,
        'patient': patient_name or (appointment.patient.user.email if appointment.patient_id else 'Sin paciente'),
        'doctor': doctor_name or (appointment.doctor.user.email if appointment.doctor_id else 'Sin doctor'),
        'time': appointment.start_time.strftime('%H:%M'),
        'status': appointment.status,
    }


def _admin_metrics(start_date, end_date, today):
    today_appointments = Appointment.objects.filter(date=today).exclude(
        status=Appointment.Status.CANCELLED,
    ).select_related('patient__user', 'doctor__user')
    new_patients_month = Patient.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )
    appointments_range = Appointment.objects.filter(date__gte=start_date, date__lte=end_date)
    total_appointments = appointments_range.exclude(status=Appointment.Status.CANCELLED).count()
    specialty_counts = (
        appointments_range.values('specialty__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    patients_by_month = (
        Patient.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    return {
        'kpis': [
            {'label': 'Citas hoy', 'value': today_appointments.count()},
            {'label': 'Total citas', 'value': total_appointments},
            {'label': 'Pacientes nuevos (mes)', 'value': new_patients_month.count()},
            {'label': 'Doctores activos', 'value': Doctor.objects.filter(active=True).count()},
            {'label': 'Usuarios inactivos', 'value': User.objects.filter(is_active=False).count()},
        ],
        'appointmentsBySpecialty': [
            {'specialty': item['specialty__name'] or 'Sin especialidad', 'count': item['count']}
            for item in specialty_counts
        ],
        'newPatientsByMonth': _format_monthly(patients_by_month),
        'todayAppointments': [_map_appointment(appt) for appt in today_appointments.order_by('start_time')[:10]],
    }


def _doctor_metrics(user, start_date, end_date, today):
    doctor = getattr(user, 'doctor_profile', None)
    if not doctor:
        return _empty_metrics()

    qs = (
        Appointment.objects.filter(doctor=doctor, date__gte=start_date, date__lte=end_date)
        .select_related('patient__user', 'doctor__user')
    )
    today_qs = qs.filter(date=today).exclude(status=Appointment.Status.CANCELLED)
    specialty_counts = (
        qs.values('specialty__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    monthly = (
        qs.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    return {
        'kpis': [
            {'label': 'Citas en rango', 'value': qs.count()},
            {'label': 'Citas hoy', 'value': today_qs.count()},
            {'label': 'Pendientes', 'value': qs.filter(status=Appointment.Status.PENDING).count()},
            {'label': 'Confirmadas', 'value': qs.filter(status=Appointment.Status.CONFIRMED).count()},
        ],
        'appointmentsBySpecialty': [
            {'specialty': item['specialty__name'] or 'Sin especialidad', 'count': item['count']}
            for item in specialty_counts
        ],
        'newPatientsByMonth': _format_monthly(monthly),
        'todayAppointments': [_map_appointment(appt) for appt in today_qs.order_by('start_time')[:10]],
    }


def _patient_metrics(user, start_date, end_date, today):
    patient = getattr(user, 'patient_profile', None)
    if not patient:
        return _empty_metrics()

    qs = (
        Appointment.objects.filter(patient=patient, date__gte=start_date, date__lte=end_date)
        .select_related('patient__user', 'doctor__user')
    )
    upcoming = qs.filter(date__gte=today).exclude(status=Appointment.Status.CANCELLED)
    today_qs = qs.filter(date=today).exclude(status=Appointment.Status.CANCELLED)
    specialty_counts = (
        qs.values('doctor__specialty__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    monthly = (
        qs.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    return {
        'kpis': [
            {'label': 'Citas programadas', 'value': upcoming.count()},
            {'label': 'Pendientes', 'value': qs.filter(status=Appointment.Status.PENDING).count()},
            {'label': 'Completadas', 'value': qs.filter(status=Appointment.Status.COMPLETED).count()},
            {'label': 'Canceladas', 'value': qs.filter(status=Appointment.Status.CANCELLED).count()},
        ],
        'appointmentsBySpecialty': [
            {
                'specialty': item['doctor__specialty__name'] or 'Sin especialidad',
                'count': item['count'],
            }
            for item in specialty_counts
        ],
        'newPatientsByMonth': _format_monthly(monthly),
        'todayAppointments': [_map_appointment(appt) for appt in today_qs.order_by('start_time')[:10]],
    }


def get_dashboard_metrics(user, start_date: date | None = None, end_date: date | None = None):
    today = timezone.now().date()
    start_date = start_date or today.replace(day=1)
    end_date = end_date or today

    if user.role == User.Roles.ADMIN:
        return _admin_metrics(start_date, end_date, today)
    if user.role == User.Roles.DOCTOR:
        return _doctor_metrics(user, start_date, end_date, today)
    if user.role == User.Roles.PATIENT:
        return _patient_metrics(user, start_date, end_date, today)
    return _empty_metrics()
