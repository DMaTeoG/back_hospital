from io import BytesIO

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def build_appointments_pdf(appointments):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(40, height - 40, 'Reporte de Citas')
    pdf.setFont('Helvetica', 10)
    y = height - 70
    for appointment in appointments:
        line = (
            f'{appointment.date} {appointment.start_time} - {appointment.patient.user.get_full_name()} '
            f'con {appointment.doctor.user.get_full_name()} ({appointment.specialty.name}) [{appointment.status}]'
        )
        pdf.drawString(40, y, line)
        y -= 14
        if y < 60:
            pdf.showPage()
            pdf.setFont('Helvetica', 10)
            y = height - 40
    pdf.setFont('Helvetica-Oblique', 9)
    pdf.drawString(40, 30, 'Generado por Hospital API')
    pdf.save()
    buffer.seek(0)
    return buffer


def build_excel(headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def build_appointments_excel(appointments):
    headers = ['ID', 'Paciente', 'Médico', 'Especialidad', 'Fecha', 'Hora Inicio', 'Hora Fin', 'Estado']
    rows = [
        [
            appointment.id,
            appointment.patient.user.get_full_name(),
            appointment.doctor.user.get_full_name(),
            appointment.specialty.name,
            appointment.date,
            appointment.start_time,
            appointment.end_time,
            appointment.status,
        ]
        for appointment in appointments
    ]
    return build_excel(headers, rows)


def build_patients_excel(patients):
    headers = ['ID', 'Nombre', 'Documento', 'Email', 'Teléfono', 'Seguro', 'Activo']
    rows = [
        [
            patient.id,
            patient.user.get_full_name(),
            patient.document,
            patient.user.email,
            patient.user.phone,
            patient.insurance,
            'Sí' if patient.active else 'No',
        ]
        for patient in patients
    ]
    return build_excel(headers, rows)
