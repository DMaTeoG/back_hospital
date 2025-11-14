from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Appointment,
    Doctor,
    EmailConfirmation,
    MedicalRecord,
    Patient,
    Schedule,
    Specialty,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserNestedSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('password',)

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class PatientSerializer(serializers.ModelSerializer):
    user = UserNestedSerializer()

    class Meta:
        model = Patient
        fields = (
            'id',
            'user',
            'document',
            'birth_date',
            'address',
            'gender',
            'emergency_contact',
            'insurance',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data.setdefault('role', User.Roles.PATIENT)
        user = UserNestedSerializer().create(user_data)
        patient = Patient.objects.create(user=user, **validated_data)
        return patient

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data:
            UserNestedSerializer().update(instance.user, user_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ('id', 'name', 'description', 'active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class DoctorSerializer(serializers.ModelSerializer):
    user = UserNestedSerializer()
    specialty_detail = SpecialtySerializer(source='specialty', read_only=True)

    class Meta:
        model = Doctor
        fields = (
            'id',
            'user',
            'specialty',
            'specialty_detail',
            'license_number',
            'bio',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data.setdefault('role', User.Roles.DOCTOR)
        user = UserNestedSerializer().create(user_data)
        doctor = Doctor.objects.create(user=user, **validated_data)
        return doctor

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data:
            UserNestedSerializer().update(instance.user, user_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ScheduleSerializer(serializers.ModelSerializer):
    doctor_detail = DoctorSerializer(source='doctor', read_only=True)

    class Meta:
        model = Schedule
        fields = (
            'id',
            'doctor',
            'doctor_detail',
            'day_of_week',
            'start_time',
            'end_time',
            'interval_minutes',
            'active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    doctor = DoctorSerializer(read_only=True)
    specialty = SpecialtySerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), source='patient', write_only=True
    )
    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), source='doctor', write_only=True
    )
    specialty_id = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.all(), source='specialty', write_only=True
    )
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id',
            'patient',
            'doctor',
            'specialty',
            'patient_id',
            'doctor_id',
            'specialty_id',
            'date',
            'start_time',
            'end_time',
            'status',
            'reason',
            'notes',
            'channel',
            'created_by',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'status', 'created_by', 'created_at', 'updated_at')


class MedicalRecordSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    doctor = DoctorSerializer(read_only=True)
    appointment = AppointmentSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), source='patient', write_only=True
    )
    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(), source='doctor', write_only=True
    )
    appointment_id = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.all(),
        source='appointment',
        write_only=True,
        allow_null=True,
        required=False,
    )

    class Meta:
        model = MedicalRecord
        fields = (
            'id',
            'patient',
            'doctor',
            'appointment',
            'patient_id',
            'doctor_id',
            'appointment_id',
            'date',
            'symptoms',
            'vitals',
            'diagnosis',
            'prescription',
            'attachments',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class EmailConfirmationSerializer(serializers.ModelSerializer):
    appointment = AppointmentSerializer(read_only=True)

    class Meta:
        model = EmailConfirmation
        fields = (
            'id',
            'appointment',
            'token',
            'expires_at',
            'confirmed',
            'sent_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class DashboardMetricsSerializer(serializers.Serializer):
    kpis = serializers.ListField(child=serializers.DictField())
    appointmentsBySpecialty = serializers.ListField(child=serializers.DictField())
    newPatientsByMonth = serializers.ListField(child=serializers.DictField())
    todayAppointments = serializers.ListField(child=serializers.DictField())
