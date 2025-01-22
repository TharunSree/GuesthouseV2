import datetime
import uuid
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
from django.utils import timezone
from django.core.validators import RegexValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


class Room(models.Model):
    ROOM_STATUS = (
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('occupied', 'Occupied'),
        ('permanent', 'Permanent'),
    )
    ROOM_TYPE = (
        ('suite', 'Suite'),
        ('normal', 'Normal'),
    )
    AC_TYPE = (
        ('ac', 'AC'),
        ('non_ac', 'Non AC'),
    )
    number = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=ROOM_STATUS, default='available')
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE)
    ac_type = models.CharField(max_length=10, choices=AC_TYPE)
    capacity = models.IntegerField()

    def __str__(self):
        return self.number

    def update_status(self):
        today = datetime.date.today()
        # Check if there are active bookings (today is within the booking's start and end date)
        active_bookings = self.bookings.filter(
            start_date__lte=today,
            end_date__gte=today
        ).exists()

        if active_bookings:
            self.status = 'booked'
        elif self.bookings.filter(status='occupied').exists():
            self.status = 'occupied'
        elif PermanentBooking.objects.filter(room=self).exists():
            self.status = 'permanent'
        else:
            self.status = 'available'


def validate_contact_length(value):
    if len(value) != 10:
        raise ValidationError('Contact number must be exactly 10 digits.')


class Tenant(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    name = models.CharField(max_length=100)
    contact = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(r'^\d{10}$', 'Enter a valid 10-digit contact number.'),
            validate_contact_length,
        ],
        help_text="Enter a 10-digit contact number."
    )
    email = models.EmailField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    class Meta:
        unique_together = ('name', 'contact', 'email')

    def __str__(self):
        return self.name


class Booking(models.Model):
    BOOKING_STATUS = (
        ('booked', 'Booked'),
        ('occupied', 'Occupied'),
    )
    room = models.ForeignKey(Room, related_name='bookings', on_delete=models.CASCADE)
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(default=datetime.date.today)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=BOOKING_STATUS, default='booked')

    def clean(self):
        # Check for permanent bookings
        if PermanentBooking.objects.filter(room=self.room).count() >= self.room.capacity:
            raise ValidationError(f"This room {self.room.number} is booked to maximum capacity.")

        # Check for overlapping temporary bookings
        overlapping_bookings = Booking.objects.filter(
            room=self.room,
        ).exclude(pk=self.pk)

        overlapping_bookings = overlapping_bookings.filter(start_date=self.start_date).exclude(
            pk=self.pk)
        if overlapping_bookings.count() >= self.room.capacity:
            raise ValidationError(f"Room {self.room.number} is fully booked during the selected dates.")

        if self.end_date < self.start_date:
            raise ValidationError("End date must be greater than start date.")

        if PermanentBooking.objects.filter(tenant=self.tenant).exists():
            raise ValidationError("This tenant already has a permanent booking.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute='0',
                hour='0',
                day_of_month=self.start_date.day,
                month_of_year=self.start_date.month,
                day_of_week='*'
            )
            # Use get_or_create to avoid duplicate PeriodicTasks
            task, task_created = PeriodicTask.objects.get_or_create(
                name=f'Update booking status {self.id}',
                defaults={
                    'crontab': schedule,
                    'task': 'availability.tasks.update_booking_status',
                    'args': json.dumps([self.id]),
                    'one_off': True
                }
            )
            if not task_created:
                # Update the task if it already exists
                task.crontab = schedule
                task.args = json.dumps([self.id])
                task.save()
        except Exception as e:
            logger.error(f"Error creating/updating PeriodicTask: {e}")
            raise

    def __str__(self):
        return f"{self.room.number} ({self.start_date} to {self.end_date})"


class PermanentBooking(models.Model):
    room = models.ForeignKey(Room, related_name='permanent_bookings', on_delete=models.CASCADE)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE)
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(null=True, blank=True)

    def clean(self):
        # Check for temporary bookings
        if Booking.objects.filter(room=self.room).count() >= self.room.capacity:
            raise ValidationError(f"This room {self.room.number} is booked to maximum capacity.")

        if Booking.objects.filter(tenant=self.tenant).exists():
            raise ValidationError("This tenant already has a temporary booking.")

    def __str__(self):
        return f"{self.room.number} (Permanent)"


@receiver(post_save, sender=Booking)
@receiver(post_save, sender=PermanentBooking)
@receiver(post_delete, sender=Booking)
@receiver(post_delete, sender=PermanentBooking)
def update_room_status(sender, instance, **kwargs):
    print(f"Signal received for {sender.__name__}: {instance}")
    instance.room.update_status()
    instance.room.save()


class ArchivedTenant(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    booking_id = models.CharField(max_length=1000)
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=10)
    email = models.EmailField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    class Meta:
        unique_together = ('name', 'contact', 'email')

    def __str__(self):
        return self.name


class ArchivedBooking(models.Model):
    STATUS_CHOICES = (
        ('expired', 'Expired'),
        ('deleted', 'Deleted'),
    )
    TYPE_CHOICES = (
        ('temporary', 'Temporary'),
        ('permanent', 'Permanent'),
    )
    booking_id = models.CharField(max_length=1000)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    tenant = models.ForeignKey(ArchivedTenant, on_delete=models.CASCADE)
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    archived_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room} - {self.tenant} ({self.status})"



