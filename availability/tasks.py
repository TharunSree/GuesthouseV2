from celery import shared_task
from .models import Booking

@shared_task
def update_booking_status(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        booking.status = 'booked'
        booking.save()
        booking.room.update_status()
        booking.room.save()
    except Booking.DoesNotExist:
        pass