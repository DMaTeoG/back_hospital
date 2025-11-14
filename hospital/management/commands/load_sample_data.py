from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import transaction


class Command(BaseCommand):
    help = 'Carga el fixture fixtures/sample_data.json a la base de datos local.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Elimina los datos existentes antes de volver a cargar el fixture.',
        )

    def handle(self, *args, **options):
        fixture_path = Path(settings.BASE_DIR) / 'fixtures' / 'sample_data.json'
        if not fixture_path.exists():
            raise CommandError(f'Fixture no encontrado: {fixture_path}')

        from hospital.models import (  # Importar aquí para evitar problemas durante collectstatic/migrate.
            Appointment,
            Doctor,
            EmailConfirmation,
            MedicalRecord,
            Patient,
            Schedule,
            Specialty,
            User,
        )

        force_load = options['force']
        dataset_exists = (
            Specialty.objects.exists()
            or Doctor.objects.exists()
            or Patient.objects.exists()
            or Appointment.objects.exists()
        )

        if dataset_exists and not force_load:
            self.stdout.write(
                self.style.WARNING('Ya existen datos. Ejecuta con --force para recargar sample_data.json.')
            )
            return

        with transaction.atomic():
            if force_load:
                # Borrar de la hoja más dependiente a la raíz para evitar errores de FK.
                for model in [
                    EmailConfirmation,
                    MedicalRecord,
                    Appointment,
                    Schedule,
                    Doctor,
                    Patient,
                    Specialty,
                    User,
                ]:
                    model.objects.all().delete()

            try:
                call_command('loaddata', str(fixture_path))
            except CommandError as exc:
                raise CommandError(f'Error al cargar sample_data.json: {exc}') from exc

        self.stdout.write(self.style.SUCCESS('Datos de ejemplo cargados correctamente.'))
