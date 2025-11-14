from datetime import date

from django.urls import reverse

from hospital.models import Appointment, EmailConfirmation
from .base import BaseAPITestCase


class AppointmentTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        login = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'admin@example.com', 'password': 'admin123'},
            format='json',
        )
        self.token = login.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def _create_payload(self, start='09:00', end='09:30'):
        return {
            'patient_id': self.patient.id,
            'doctor_id': self.doctor.id,
            'specialty_id': self.specialty.id,
            'date': date.today().isoformat(),
            'start_time': start,
            'end_time': end,
            'channel': Appointment.Channel.PRESENTIAL,
            'reason': 'Control',
        }

    def test_create_appointment_generates_confirmation(self):
        response = self.client.post(reverse('appointment-list'), self._create_payload(), format='json')
        self.assertEqual(response.status_code, 201)
        appointment_id = response.data['id']
        confirmation = EmailConfirmation.objects.get(appointment_id=appointment_id)
        self.assertTrue(confirmation.token)

    def test_prevent_overlapping_appointments(self):
        self.client.post(reverse('appointment-list'), self._create_payload(), format='json')
        response = self.client.post(
            reverse('appointment-list'),
            self._create_payload(start='09:15', end='09:45'),
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_email_confirmation_endpoint(self):
        response = self.client.post(reverse('appointment-list'), self._create_payload(), format='json')
        appointment_id = response.data['id']
        confirmation = EmailConfirmation.objects.get(appointment_id=appointment_id)
        url = reverse('email_confirm')
        confirm_response = self.client.get(f'{url}?token={confirmation.token}')
        self.assertEqual(confirm_response.status_code, 200)
        confirmation.refresh_from_db()
        appointment = Appointment.objects.get(id=appointment_id)
        self.assertTrue(confirmation.confirmed)
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
