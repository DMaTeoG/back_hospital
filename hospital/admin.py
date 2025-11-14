from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    Appointment,
    AuditLog,
    Doctor,
    EmailConfirmation,
    MedicalRecord,
    Patient,
    Schedule,
    Specialty,
    User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone')}),
        (
            _('Permissions'),
            {
                'fields': (
                    'role',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2', 'role'),
            },
        ),
    )


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'document', 'insurance', 'active')
    search_fields = ('user__first_name', 'user__last_name', 'document')
    list_filter = ('active',)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'specialty', 'license_number', 'active')
    search_fields = ('user__first_name', 'user__last_name', 'license_number')
    list_filter = ('specialty', 'active')


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    search_fields = ('name',)
    list_filter = ('active',)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'day_of_week', 'start_time', 'end_time', 'active')
    list_filter = ('day_of_week', 'active')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'date',
        'start_time',
        'doctor',
        'patient',
        'status',
    )
    list_filter = ('status', 'date', 'specialty')
    search_fields = (
        'patient__user__first_name',
        'patient__user__last_name',
        'doctor__user__first_name',
        'doctor__user__last_name',
    )


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'date')
    search_fields = ('patient__user__first_name', 'patient__user__last_name')
    list_filter = ('doctor', 'date')


@admin.register(EmailConfirmation)
class EmailConfirmationAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'token', 'confirmed', 'expires_at')
    search_fields = ('appointment__patient__user__email',)
    list_filter = ('confirmed',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'entity', 'entity_id', 'user', 'created_at')
    list_filter = ('action', 'entity')
    search_fields = ('entity', 'entity_id')
