from datetime import date, time

from django.urls import reverse

from hospital.models import Appointment
from .base import BaseAPITestCase


class DashboardTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'admin@example.com', 'password': 'admin123'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')

    def test_dashboard_metrics_returns_payload(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            specialty=self.specialty,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(10, 30),
        )
        url = reverse('dashboard_metrics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for key in [
            'kpis',
            'appointmentsBySpecialty',
            'newPatientsByMonth',
            'todayAppointments',
        ]:
            self.assertIn(key, response.data)
