from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from hospital.models import Doctor, Patient, Specialty

User = get_user_model()


class BaseAPITestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.specialty = Specialty.objects.create(name='Cardiología')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='admin123')
        self.doctor_user = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            role=User.Roles.DOCTOR,
            first_name='Doc',
            last_name='McStuff',
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            specialty=self.specialty,
            license_number='LIC123',
        )
        self.patient_user = User.objects.create_user(
            email='patient@example.com',
            password='patient123',
            role=User.Roles.PATIENT,
            first_name='Pat',
            last_name='Smith',
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            document='ABC123',
            address='123 Street',
        )
