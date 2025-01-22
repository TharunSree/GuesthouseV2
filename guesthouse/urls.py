from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from availability import views
from availability.views import *

urlpatterns = [
    path('rebook_archived_tenant/<int:archived_tenant_id>/',
         views.rebook_archived_tenant, name='rebook_archived_tenant'),
    path('confirm_add_tenant/', views.confirm_add_tenant, name='confirm_add_tenant'),
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('room-allotment/', views.room_allotment, name='room-allotment'),
    path('perm-room-allotment/', perm_room_allotment, name='perm-room-allotment'),
    path('room-chart/', views.room_chart, name='room-chart'),
    path('occupants/', views.occupants, name='occupants'),
    path('past-occupants/', views.past_occupants, name='past-occupants'),
    path('add-tenant/', add_tenant, name='add-tenant'),
    path('edit-tenant/<str:pk>/', edit_tenant, name='edit-tenant'),
    path('delete-tenant/<int:tenant_id>/', views.delete_tenant, name='delete-tenant'),
    path('rooms/', views.rooms, name='rooms'),
    path('add-temp-booking/', add_temp_booking, name='add-temp-booking'),
    path('edit-temp-booking/<int:pk>/', edit_temp_booking, name='edit-temp-booking'),
    path('delete-booking/<int:booking_id>/', delete_booking, name='delete-booking'),
    path('add-perm-booking/', add_perm_booking, name='add-perm-booking'),
    path('edit-perm-booking/<int:pk>/', edit_perm_booking, name='edit-perm-booking'),
    path('perm-delete-booking/<int:booking_id>/', perm_delete_booking, name='perm-delete-booking'),
    path('add-room/', add_room, name='add-room'),
    path('edit-room/<int:pk>/', edit_room, name='edit-room'),
    path('delete-room/<int:room_id>/', views.delete_room, name='delete-room'),
    path('past-booking/', past_room_allotment, name='past-booking'),
    path('generate-pdf/', views.generate_pdf, name='generate_pdf'),
    path('temp-generate-pdf/', views.generate_temp_pdf, name='temp_generate_pdf'),
    path('past-generate-pdf/', views.generate_past_pdf, name='past_generate_pdf'),
    path('guest-pdf/', views.generate_guest_pdf, name='guest_pdf'),
    path('guest-past-pdf/', views.generate_past_guest_pdf, name='guest_past_pdf'),
    path('room_history_pdf/<str:selected_room>/', views.generate_room_history_pdf, name='room_history_pdf'),
    path('delete-expired-bookings/', run_delete_expired_bookings, name='delete-expired-bookings'),
    path('room_history/', room_history, name='room_history'),
    path('available_rooms/',views.available_rooms, name="available_rooms")

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
