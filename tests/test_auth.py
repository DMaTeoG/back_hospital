from datetime import date, time

from django.urls import reverse

from hospital.models import Appointment
from .base import BaseAPITestCase


class AuthTests(BaseAPITestCase):
    def _get_token(self, email, password):
        url = reverse('token_obtain_pair')
        response = self.client.post(url, {'email': email, 'password': password}, format='json')
        self.assertEqual(response.status_code, 200)
        return response.data['access']

    def test_login_returns_tokens(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'admin@example.com', 'password': 'admin123'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_doctor_only_sees_their_patients(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            specialty=self.specialty,
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        token = self._get_token('doctor@example.com', 'doctor123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('patient-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_patient_only_sees_self(self):
        token = self._get_token('patient@example.com', 'patient123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('patient-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
