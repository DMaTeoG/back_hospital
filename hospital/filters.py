import django_filters
from django.db import models

from .models import Appointment, Doctor, MedicalRecord, Patient, Schedule


class PatientFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Patient
        fields = ['active']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            models.Q(user__first_name__icontains=value)
            | models.Q(user__last_name__icontains=value)
            | models.Q(document__icontains=value)
        )


class DoctorFilter(django_filters.FilterSet):
    specialty = django_filters.NumberFilter(field_name='specialty_id')
    active = django_filters.BooleanFilter()

    class Meta:
        model = Doctor
        fields = ['specialty', 'active']


class ScheduleFilter(django_filters.FilterSet):
    doctor = django_filters.NumberFilter(field_name='doctor_id')
    active = django_filters.BooleanFilter()

    class Meta:
        model = Schedule
        fields = ['doctor', 'day_of_week', 'active']


class AppointmentFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status')

    class Meta:
        model = Appointment
        fields = ['doctor', 'patient', 'status']


class MedicalRecordFilter(django_filters.FilterSet):
    patient = django_filters.NumberFilter(field_name='patient_id')
    doctor = django_filters.NumberFilter(field_name='doctor_id')
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model = MedicalRecord
        fields = ['patient', 'doctor']
