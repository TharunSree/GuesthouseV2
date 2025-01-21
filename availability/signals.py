import uuid
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import IntegrityError
from .models import Booking, Room, PermanentBooking, ArchivedBooking, ArchivedTenant


@receiver(post_save, sender=Booking)
def update_room_status(sender, instance, created, **kwargs):
    if created:
        # New booking created, update room status to 'booked'
        instance.room.status = 'booked'
        instance.room.save()
    else:
        # Existing booking updated
        if instance.end_date <= timezone.now().date():
            # Booking end date has passed, update room status to 'available'
            instance.room.status = 'available'
            instance.room.save()


@receiver(post_save, sender=PermanentBooking)
def remove_permanent_booking(sender, instance, created, **kwargs):
    if not created:
        # Existing permanent booking updated, remove it
        instance.delete()


@receiver(post_delete, sender=PermanentBooking)
def set_end_date_on_delete(sender, instance, **kwargs):
    instance.end_date = timezone.now().date()
    instance.save()


@receiver(post_delete, sender=PermanentBooking)
@receiver(post_delete, sender=Booking)
def archive_booking(sender, instance, **kwargs):
    tenant = instance.tenant
    archived_tenant, created = ArchivedTenant.objects.get_or_create(
        name=tenant.name,
        contact=tenant.contact,
        email=tenant.email,
        defaults={
            'address': tenant.address,
            'gender': tenant.gender,
        }
    )

    if not created:
        # If the tenant already exists, update the existing tenant's details
        archived_tenant.address = tenant.address
        archived_tenant.gender = tenant.gender
        archived_tenant.save()

    ArchivedBooking.objects.create(
        booking_id=str(uuid.uuid4()),
        room=instance.room,
        tenant=archived_tenant,
        checkin_date=instance.start_date,
        checkout_date=instance.end_date or timezone.now().date(),
        status='deleted' if sender == PermanentBooking else 'expired',
        type='permanent' if sender == PermanentBooking else 'temporary',
    )
