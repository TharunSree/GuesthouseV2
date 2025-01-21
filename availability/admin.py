# availability/admin.py

from django.contrib import admin
from .models import Room, Booking, PermanentBooking, Tenant, ArchivedBooking, ArchivedTenant


class RoomAdmin(admin.ModelAdmin):
    list_display = ['number', 'room_type', 'ac_type', 'capacity', 'status']
    list_filter = ['room_type', 'ac_type', 'status']


class BookingAdmin(admin.ModelAdmin):
    list_display = ['room', 'start_date', 'end_date', 'tenant', 'status']
    list_filter = ['status', 'room']

    def tenant_name(self, obj):
        return obj.tenant.name

    def tenant_contact(self, obj):
        return obj.tenant.contact

    def tenant_email(self, obj):
        return obj.tenant.email

    def tenant_address(self, obj):
        return obj.tenant.address


class PermanentBookingAdmin(admin.ModelAdmin):
    list_display = ['room', 'tenant']
    list_filter = ['room']

    def tenant_name(self, obj):
        return obj.tenant.name

    def tenant_contact(self, obj):
        return obj.tenant.contact

    def tenant_email(self, obj):
        return obj.tenant.email

    def tenant_address(self, obj):
        return obj.tenant.address


admin.site.register(Room, RoomAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(PermanentBooking, PermanentBookingAdmin)
admin.site.register(Tenant)
admin.site.register(ArchivedBooking)
admin.site.register(ArchivedTenant)

