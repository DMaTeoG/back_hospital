from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_staff', False)
        if extra_fields.get('role') is None:
            extra_fields['role'] = User.Roles.PATIENT
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('role', User.Roles.ADMIN)
        if extra_fields.get('is_staff') is not True or extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_staff=True e is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        DOCTOR = 'DOCTOR', 'Médico'
        PATIENT = 'PATIENT', 'Paciente'

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.PATIENT)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self) -> str:
        return f'{self.get_full_name() or self.email} ({self.role})'


class Patient(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = 'M', 'Masculino'
        FEMALE = 'F', 'Femenino'
        OTHER = 'O', 'Otro'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    document = models.CharField(max_length=50, unique=True)
    birth_date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    insurance = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f'Paciente: {self.user.get_full_name()}'


class Specialty(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Specialties'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Doctor(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, related_name='doctors')
    license_number = models.CharField(max_length=80, unique=True)
    bio = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f'Dr. {self.user.get_full_name()} - {self.specialty.name}'


class Schedule(TimeStampedModel):
    class Days(models.IntegerChoices):
        MONDAY = 0, 'Lunes'
        TUESDAY = 1, 'Martes'
        WEDNESDAY = 2, 'Miércoles'
        THURSDAY = 3, 'Jueves'
        FRIDAY = 4, 'Viernes'
        SATURDAY = 5, 'Sábado'
        SUNDAY = 6, 'Domingo'

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=Days.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    interval_minutes = models.PositiveIntegerField(default=30)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('doctor', 'day_of_week', 'start_time', 'end_time')
        ordering = ['doctor', 'day_of_week', 'start_time']

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('La hora de inicio debe ser menor a la hora de fin.')

        if self.doctor_id is None:
            raise ValidationError('El horario debe estar asociado a un médico.')

        overlapping = Schedule.objects.filter(
            doctor=self.doctor,
            day_of_week=self.day_of_week,
            active=True,
        ).exclude(id=self.id)

        if overlapping.filter(start_time__lt=self.end_time, end_time__gt=self.start_time).exists():
            raise ValidationError('El médico ya tiene un horario creado en ese rango.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.doctor} - {self.get_day_of_week_display()}'


class Appointment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        CONFIRMED = 'CONFIRMED', 'Confirmada'
        CANCELLED = 'CANCELLED', 'Cancelada'
        COMPLETED = 'COMPLETED', 'Completada'

    class Channel(models.TextChoices):
        PRESENTIAL = 'PRESENTIAL', 'Presencial'
        VIRTUAL = 'VIRTUAL', 'Virtual'

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    specialty = models.ForeignKey(Specialty, on_delete=models.PROTECT, related_name='appointments')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.PRESENTIAL)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_appointments',
    )

    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [models.Index(fields=['doctor', 'date', 'start_time', 'status'])]

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError('La hora de inicio debe ser menor a la hora de fin.')
        overlapping = (
            Appointment.objects.filter(doctor=self.doctor, date=self.date)
            .exclude(id=self.id)
            .exclude(status=Appointment.Status.CANCELLED)
            .filter(start_time__lt=self.end_time, end_time__gt=self.start_time)
        )
        if overlapping.exists():
            raise ValidationError('El médico ya tiene una cita en ese horario.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'Cita {self.date} {self.start_time} - {self.doctor}'


class MedicalRecord(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='records')
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='records'
    )
    date = models.DateField(default=timezone.now)
    symptoms = models.TextField(blank=True)
    vitals = models.JSONField(default=dict, blank=True)
    diagnosis = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self) -> str:
        return f'Historia {self.patient} {self.date}'


class EmailConfirmation(TimeStampedModel):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='confirmation')
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4().hex)
    expires_at = models.DateTimeField()
    confirmed = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    def refresh_token(self):
        self.token = uuid.uuid4().hex
        self.expires_at = timezone.now() + timedelta(hours=getattr(settings, 'EMAIL_CONFIRMATION_HOURS', 48))
        self.confirmed = False
        self.sent_at = None

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                hours=getattr(settings, 'EMAIL_CONFIRMATION_HOURS', 48)
            )
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'Confirmación {self.appointment_id}'


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    entity = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.action} {self.entity}#{self.entity_id}'
