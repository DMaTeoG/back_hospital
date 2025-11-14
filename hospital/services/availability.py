from datetime import datetime, timedelta

from django.utils import timezone

from ..models import Appointment, Schedule


def get_doctor_availability(doctor_id, date):
    weekday = date.weekday()
    schedules = Schedule.objects.filter(doctor_id=doctor_id, day_of_week=weekday, active=True)
    appointments = (
        Appointment.objects.filter(doctor_id=doctor_id, date=date)
        .exclude(status=Appointment.Status.CANCELLED)
        .values_list('start_time', 'end_time')
    )
    booked = {(start, end) for start, end in appointments}

    available_slots = []
    for schedule in schedules:
        current = datetime.combine(date, schedule.start_time)
        end = datetime.combine(date, schedule.end_time)
        delta = timedelta(minutes=schedule.interval_minutes)
        while current + delta <= end:
            slot_start = current.time()
            slot_end = (current + delta).time()
            slot_tuple = (slot_start, slot_end)
            if slot_tuple not in booked:
                available_slots.append(
                    {
                        'start_time': slot_start.strftime('%H:%M'),
                        'end_time': slot_end.strftime('%H:%M'),
                    }
                )
            current += delta
    return available_slots
