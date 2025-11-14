from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    AppointmentViewSet,
    AuthMeView,
    DashboardMetricsView,
    DoctorViewSet,
    EmailConfirmView,
    ExportAppointmentsExcelView,
    ExportAppointmentsPDFView,
    ExportPatientsExcelView,
    MedicalRecordViewSet,
    PatientViewSet,
    RegisterView,
    ScheduleViewSet,
    SpecialtyViewSet,
    UserViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'users', UserViewSet, basename='user')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'specialties', SpecialtyViewSet, basename='specialty')
router.register(r'schedules', ScheduleViewSet, basename='schedule')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'records', MedicalRecordViewSet, basename='record')

urlpatterns = [
    path('auth/login', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me', AuthMeView.as_view(), name='auth_me'),
    path('auth/register', RegisterView.as_view(), name='auth_register'),
    path('dashboard/metrics', DashboardMetricsView.as_view(), name='dashboard_metrics'),
    path('export/appointments.pdf', ExportAppointmentsPDFView.as_view(), name='export_appointments_pdf'),
    path('export/appointments.xlsx', ExportAppointmentsExcelView.as_view(), name='export_appointments_excel'),
    path('export/patients.xlsx', ExportPatientsExcelView.as_view(), name='export_patients_excel'),
    path('email/confirm', EmailConfirmView.as_view(), name='email_confirm'),
    path('', include(router.urls)),
]
