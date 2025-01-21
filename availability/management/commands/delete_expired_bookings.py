from django.core.management.base import BaseCommand
from django.utils import timezone
from availability.models import Booking, ArchivedBooking, ArchivedTenant


class Command(BaseCommand):
    help = 'Deletes expired temporary bookings and archives them'

    def handle(self, *args, **kwargs):
        expired_date = timezone.now() - timezone.timedelta(days=1)
        expired_bookings = Booking.objects.filter(end_date__lte=expired_date)

        for booking in expired_bookings:
            # Archive tenant details
            archived_tenant = ArchivedTenant.objects.create(
                booking_id=booking.id,
                name=booking.tenant.name,
                contact=booking.tenant.contact,
                email=booking.tenant.email,
                address=booking.tenant.address,
                gender=booking.tenant.gender,
            )

            # Create archived booking with archived tenant
            archived_booking = ArchivedBooking.objects.create(
                booking_id=booking.id,
                room=booking.room,
                tenant=archived_tenant,
                checkin_date=booking.start_date,
                checkout_date=booking.end_date,
                status='expired'
            )

            # Delete the original tenant
            booking.tenant.delete()

        # Delete expired bookings
        expired_bookings.delete()

        self.stdout.write(self.style.SUCCESS('Expired bookings archived and deleted successfully'))
