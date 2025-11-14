from __future__ import annotations

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import AppointmentFilter, DoctorFilter, MedicalRecordFilter, PatientFilter, ScheduleFilter
from .models import (
    Appointment,
    AuditLog,
    Doctor,
    EmailConfirmation,
    MedicalRecord,
    Patient,
    Schedule,
    Specialty,
)
from .permissions import IsAdminOrReadOnly, IsAdminRole
from .serializers import (
    AppointmentSerializer,
    DashboardMetricsSerializer,
    DoctorSerializer,
    EmailConfirmationSerializer,
    MedicalRecordSerializer,
    PatientSerializer,
    ScheduleSerializer,
    SpecialtySerializer,
    UserNestedSerializer,
    UserSerializer,
)
from .services.availability import get_doctor_availability
from .services.dashboard import get_dashboard_metrics
from .services.exports import build_appointments_excel, build_appointments_pdf, build_patients_excel
from .tasks import send_confirmation_email_task
from .utils import register_audit

User = get_user_model()


class AuthMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PatientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        register_audit(patient.user, 'register', 'Patient', patient.id, serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserNestedSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        register_audit(request.user, 'activate_user', 'User', user.id)
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        register_audit(request.user, 'deactivate_user', 'User', user.id)
        return Response(UserSerializer(user).data)


class SpecialtyViewSet(viewsets.ModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['active']
    search_fields = ['name']


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    filterset_class = PatientFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Patient.objects.select_related('user')
        if user.role == User.Roles.ADMIN:
            return qs.order_by('id')
        if user.role == User.Roles.DOCTOR:
            return qs.filter(appointments__doctor__user=user).distinct().order_by('id')
        return qs.filter(user=user).order_by('id')

    def perform_create(self, serializer):
        if self.request.user.role not in [User.Roles.ADMIN, User.Roles.DOCTOR]:
            raise PermissionDenied('Solo administradores o médicos pueden crear pacientes.')
        patient = serializer.save()
        register_audit(self.request.user, 'create', 'Patient', patient.id, serializer.data)

    def perform_update(self, serializer):
        patient = serializer.save()
        register_audit(self.request.user, 'update', 'Patient', patient.id, serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        term = request.query_params.get('q', '')
        qs = self.get_queryset().filter(
            Q(user__first_name__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(document__icontains=term)
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.select_related('user', 'specialty')
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = DoctorFilter

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        if user.role == User.Roles.ADMIN:
            return qs
        if user.role == User.Roles.DOCTOR:
            return qs.filter(user=user)
        return qs.filter(active=True)

    def perform_create(self, serializer):
        if self.request.user.role != User.Roles.ADMIN:
            raise PermissionDenied('Solo administradores pueden crear médicos.')
        doctor = serializer.save()
        register_audit(self.request.user, 'create', 'Doctor', doctor.id, serializer.data)

    def perform_update(self, serializer):
        if self.request.user.role != User.Roles.ADMIN and serializer.instance.user != self.request.user:
            raise PermissionDenied('No puedes modificar otros médicos.')
        doctor = serializer.save()
        register_audit(self.request.user, 'update', 'Doctor', doctor.id, serializer.data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        doctor = self.get_object()
        schedules = doctor.schedules.filter(active=True)
        serializer = ScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-specialty/(?P<specialty_id>[^/.]+)')
    def by_specialty(self, request, specialty_id=None):
        qs = self.get_queryset().filter(specialty_id=specialty_id, active=True)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    filterset_class = ScheduleFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Schedule.objects.select_related('doctor', 'doctor__user')
        if user.role == User.Roles.ADMIN:
            return qs
        if user.role == User.Roles.DOCTOR:
            return qs.filter(doctor__user=user)
        raise PermissionDenied('No tienes permisos para ver horarios.')

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == User.Roles.DOCTOR:
            schedule = serializer.save(doctor=user.doctor_profile)
        elif user.role == User.Roles.ADMIN:
            schedule = serializer.save()
        else:
            raise PermissionDenied('Solo administradores o médicos.')
        register_audit(user, 'create', 'Schedule', schedule.id, serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    filterset_class = AppointmentFilter
    permission_classes = [permissions.IsAuthenticated]
    queryset = Appointment.objects.select_related(
        'patient__user', 'doctor__user', 'specialty', 'created_by'
    )

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Roles.ADMIN:
            return self.queryset
        if user.role == User.Roles.DOCTOR:
            return self.queryset.filter(doctor__user=user)
        return self.queryset.filter(patient__user=user)

    def _validate_participants(self, serializer):
        data = serializer.validated_data
        patient = data.get('patient') or getattr(serializer.instance, 'patient', None)
        doctor = data.get('doctor') or getattr(serializer.instance, 'doctor', None)
        specialty = data.get('specialty') or doctor.specialty
        if not patient or not doctor:
            raise ValidationError('La cita requiere paciente y médico')
        if specialty != doctor.specialty:
            raise ValidationError('La cita debe usar la especialidad del médico.')
        if self.request.user.role == User.Roles.PATIENT and patient.user != self.request.user:
            raise PermissionDenied('Los pacientes solo pueden crear/editar sus citas.')
        return specialty

    def perform_create(self, serializer):
        specialty = self._validate_participants(serializer)
        try:
            appointment = serializer.save(created_by=self.request.user, specialty=specialty)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict or exc.message)
        confirmation, _ = EmailConfirmation.objects.get_or_create(appointment=appointment)
        confirmation.refresh_token()
        confirmation.save()
        send_confirmation_email_task.delay(confirmation.id)
        register_audit(self.request.user, 'create', 'Appointment', appointment.id, serializer.data)

    def perform_update(self, serializer):
        specialty = self._validate_participants(serializer)
        try:
            appointment = serializer.save(specialty=specialty)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict or exc.message)
        register_audit(self.request.user, 'update', 'Appointment', appointment.id, serializer.data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save(update_fields=['status'])
        register_audit(request.user, 'confirm', 'Appointment', appointment.id)
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=['status'])
        register_audit(request.user, 'cancel', 'Appointment', appointment.id)
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=False, methods=['get'])
    def availability(self, request):
        doctor_id = request.query_params.get('doctor_id')
        date_str = request.query_params.get('date')
        if not date_str:
            raise ValidationError('date es obligatorio')

        if not doctor_id:
            user = request.user
            if user.role == User.Roles.DOCTOR:
                doctor_profile = getattr(user, 'doctor_profile', None)
                if not doctor_profile:
                    raise ValidationError('El usuario no tiene perfil de doctor asociado.')
                doctor_id = doctor_profile.id
            else:
                raise ValidationError('doctor_id es obligatorio')

        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        slots = get_doctor_availability(doctor_id, date_obj)
        return Response(slots)


class MedicalRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalRecordSerializer
    filterset_class = MedicalRecordFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = MedicalRecord.objects.select_related(
            'patient__user',
            'doctor__user',
            'appointment',
        )
        if user.role == User.Roles.ADMIN:
            return qs
        if user.role == User.Roles.DOCTOR:
            return qs.filter(doctor__user=user)
        return qs.filter(patient__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in [User.Roles.ADMIN, User.Roles.DOCTOR]:
            raise PermissionDenied('Solo médicos o administradores pueden crear historias.')
        if user.role == User.Roles.DOCTOR and serializer.validated_data['doctor'].user != user:
            raise PermissionDenied('Solo puedes registrar historias de tus pacientes.')
        record = serializer.save()
        register_audit(user, 'create', 'MedicalRecord', record.id, serializer.data)

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == User.Roles.DOCTOR and serializer.instance.doctor.user != user:
            raise PermissionDenied('Solo puedes editar tus historias.')
        record = serializer.save()
        register_audit(user, 'update', 'MedicalRecord', record.id, serializer.data)

    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)')
    def by_patient(self, request, patient_id=None):
        qs = self.get_queryset().filter(patient_id=patient_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='appointment/(?P<appointment_id>[^/.]+)')
    def by_appointment(self, request, appointment_id=None):
        qs = self.get_queryset().filter(appointment_id=appointment_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DashboardMetricsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        start = request.query_params.get('from')
        end = request.query_params.get('to')
        start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else None
        end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else None
        data = get_dashboard_metrics(request.user, start_date, end_date)
        return Response(data)


class ExportAppointmentsPDFView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        appointments = AppointmentViewSet.queryset.all()
        buffer = build_appointments_pdf(appointments)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="appointments.pdf"'
        return response


class ExportAppointmentsExcelView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        appointments = AppointmentViewSet.queryset.all()
        buffer = build_appointments_excel(appointments)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="appointments.xlsx"'
        return response


class ExportPatientsExcelView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        patients = Patient.objects.select_related('user').all()
        buffer = build_patients_excel(patients)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="patients.xlsx"'
        return response


class EmailConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        confirmation = get_object_or_404(EmailConfirmation, token=token)
        if confirmation.expires_at < timezone.now():
            return Response({'detail': 'Token expirado'}, status=status.HTTP_400_BAD_REQUEST)
        confirmation.confirmed = True
        confirmation.appointment.status = Appointment.Status.CONFIRMED
        confirmation.appointment.save(update_fields=['status'])
        confirmation.save(update_fields=['confirmed'])
        return Response({'detail': 'Cita confirmada'})
