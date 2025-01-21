# availability/views.py
import weasyprint
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import date as dt, timedelta
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from .models import Room, Booking, PermanentBooking, Tenant, ArchivedBooking, ArchivedTenant
from django.contrib.auth.decorators import login_required
from .forms import BookingForm, PermBookingForm, AddRoomForm, AddTenantForm
from django.core.management import call_command


def index(request):
    rooms = Room.objects.all()
    bookings = Booking.objects.all()
    permanent_bookings = PermanentBooking.objects.all()
    dates = [dt.today() + timedelta(days=i) for i in range(31)]

    # Initialize availability dictionary with two 'Available' statuses for each date
    availability = {room.number: {date: ['Available' for __ in range(room.capacity)] for date in dates} for room in
                    rooms}

    # Update availability based on temporary bookings
    for booking in bookings:
        for date in dates:
            if booking.start_date <= date <= booking.end_date:
                # Find the first available slot in the availability dictionary for the current date
                slot_index = availability[booking.room.number][date].index('Available')
                # Update the slot with the booking status
                availability[booking.room.number][date][slot_index] = booking.status

    # Update availability based on permanent bookings
    for permanent_booking in permanent_bookings:
        for date in dates:
            # Find the first available slot in the availability dictionary for the current date
            slot_index = availability[permanent_booking.room.number][date].index('Available')
            # Update the slot with the permanent booking status
            availability[permanent_booking.room.number][date][slot_index] = 'Permanent'

    context = {
        'rooms': rooms,
        'dates': dates,
        'availability': availability,
    }
    return render(request, 'availability/index.html', context)


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('room-allotment')  # Redirect to the home page after successful login
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')  # Redirect to your desired page after login


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def rooms(request):
    rooms = Room.objects.all()
    rooms_with_free_slots = []

    for room in rooms:
        start_date = dt.today()  # Example: today's date
        # Example: tomorrow's date
        # Calculate the number of current bookings
        temporary_bookings_count = Booking.objects.filter(room=room, start_date=start_date).count()
        permanent_bookings_count = PermanentBooking.objects.filter(room=room).count()
        current_bookings_count = temporary_bookings_count + permanent_bookings_count

        free_slots = room.capacity - current_bookings_count

        # Determine room statuses
        statuses = set()
        if room.status == 'occupied':
            statuses.add('occupied')
        elif room.status == 'booked':
            statuses.add('booked')
        elif room.status == 'available':
            statuses.add('available')
        if permanent_bookings_count > 0:
            statuses.add('permanent')

        rooms_with_free_slots.append({
            'room': room,
            'free_slots': free_slots,
            'statuses': list(statuses),  # Add statuses to the context
        })

    context = {
        'rooms_with_free_slots': rooms_with_free_slots,
    }
    return render(request, 'rooms.html', context)


@csrf_exempt
def rebook_archived_tenant(request, archived_tenant_id):
    if request.method == 'POST':
        try:
            # Retrieve the archived tenant
            archived_tenant = get_object_or_404(ArchivedTenant, id=archived_tenant_id)

            # Check if a tenant with the same details already exists
            existing_tenant = Tenant.objects.filter(
                name=archived_tenant.name,
                contact=archived_tenant.contact,
                email=archived_tenant.email
            ).first()

            if existing_tenant:
                tenant = existing_tenant
            else:
                # Create a new tenant with the same details
                tenant = Tenant.objects.create(
                    name=archived_tenant.name,
                    contact=archived_tenant.contact,
                    email=archived_tenant.email,
                    address=archived_tenant.address,
                    gender=archived_tenant.gender
                )

            # Delete the corresponding archived tenant
            archived_tenant.delete()

            return JsonResponse({'success': True})
        except ArchivedTenant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ArchivedTenant does not exist'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@csrf_exempt
def check_past_tenant(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contact = request.POST.get('contact')
        email = request.POST.get('email')

        # Check if the tenant exists in past tenants
        past_tenant = ArchivedTenant.objects.filter(name=name, contact=contact, email=email).exists()
        return JsonResponse({'exists': past_tenant})
    return JsonResponse({'exists': False})


@login_required
def room_allotment(request):
    rooms = Room.objects.all()
    temporary_bookings = Booking.objects.select_related('tenant').all()
    booking = Booking.objects.all().__len__()

    context = {
        'rooms': rooms,
        'temporary_bookings': temporary_bookings,
        'booking': booking,
    }
    return render(request, 'room-allotment.html', context)


@login_required
def perm_room_allotment(request):
    rooms = Room.objects.all()
    permanent_bookings = PermanentBooking.objects.select_related('tenant').all()
    booking = PermanentBooking.objects.all().__len__()

    context = {
        'rooms': rooms,
        'permanent_bookings': permanent_bookings,
        'booking': booking,
    }
    return render(request, 'permanent-room-allotment.html', context)


@login_required
def past_room_allotment(request):
    rooms = Room.objects.all()
    past_bookings = ArchivedBooking.objects.select_related('tenant').all()
    bookings = ArchivedBooking.objects.all().__len__()

    context = {
        'rooms': rooms,
        'past_bookings': past_bookings,
        'bookings': bookings,
    }
    return render(request, 'past-bookings.html', context)


@login_required
def occupants(request):
    rooms = Room.objects.all()
    temporary_bookings = Booking.objects.select_related('tenant').all()
    permanent_bookings = PermanentBooking.objects.select_related('tenant').all()
    tenant = Tenant.objects.all()
    guests = Tenant.objects.all().__len__()

    context = {
        'rooms': rooms,
        'temporary_bookings': temporary_bookings,
        'permanent_bookings': permanent_bookings,
        'tenants': tenant,
        'guests': guests,
    }
    return render(request, 'occupants.html', context)


@login_required
def past_occupants(request):
    rooms = Room.objects.all()
    temporary_bookings = Booking.objects.select_related('tenant').all()
    permanent_bookings = PermanentBooking.objects.select_related('tenant').all()
    tenant = ArchivedTenant.objects.all()
    guests = ArchivedTenant.objects.all().__len__()
    context = {
        'rooms': rooms,
        'temporary_bookings': temporary_bookings,
        'permanent_bookings': permanent_bookings,
        'tenants': tenant,
        'guests': guests,
    }
    return render(request, 'past-occupants.html', context)


@login_required
def room_chart(request):
    rooms = Room.objects.all()
    bookings = Booking.objects.all()
    permanent_bookings = PermanentBooking.objects.all()
    dates = [dt.today() + timedelta(days=i) for i in range(31)]

    # Initialize availability dictionary with two 'Available' statuses for each date
    availability = {room.number: {date: ['Available' for __ in range(room.capacity)] for date in dates} for room in
                    rooms}
    booking = Booking.objects.all().__len__() + PermanentBooking.objects.all().__len__()

    if booking:
        # Update availability based on temporary bookings
        for booking in bookings:
            for date in dates:
                if booking.start_date <= date <= booking.end_date:
                    # Find the first available slot in the availability dictionary for the current date
                    slot_index = availability[booking.room.number][date].index('Available')
                    # Update the slot with the booking status
                    availability[booking.room.number][date][slot_index] = booking.status

        # Update availability based on permanent bookings
        for permanent_booking in permanent_bookings:
            for date in dates:
                # Find the first available slot in the availability dictionary for the current date
                slot_index = availability[permanent_booking.room.number][date].index('Available')
                # Update the slot with the permanent booking status
                availability[permanent_booking.room.number][date][slot_index] = 'Permanent'

    context = {
        'rooms': rooms,
        'dates': dates,
        'availability': availability,
        'booking': booking,
    }
    return render(request, 'room-chart.html', context)


@login_required
def add_temp_booking(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('room-allotment')
    else:
        form = BookingForm()
    return render(request, 'room-book-temp.html', {'form': form})


@login_required()
def edit_temp_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            return redirect('room-allotment')
    else:
        form = BookingForm(instance=booking)
    return render(request, 'room-book-temp.html', {'form': form})


@login_required
def delete_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id)
        archived_tenant = ArchivedTenant.objects.create(
            booking_id=booking.id,
            name=booking.tenant.name,
            contact=booking.tenant.contact,
            email=booking.tenant.email,
            address=booking.tenant.address,
            gender=booking.tenant.gender,
        )
        archived_booking = ArchivedBooking(
            booking_id=booking.id,
            room=booking.room,
            tenant=archived_tenant,
            checkin_date=str(booking.start_date),
            checkout_date=str(booking.end_date),
            status='deleted'
        )
        archived_booking.save()
        booking.tenant.delete()
        booking.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required
def add_perm_booking(request):
    if request.method == 'POST':
        form = PermBookingForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('perm-room-allotment')
    else:
        form = PermBookingForm()
    return render(request, 'room-book-perm.html', {'form': form})


@login_required()
def edit_perm_booking(request, pk):
    booking = get_object_or_404(PermanentBooking, pk=pk)
    if request.method == 'POST':
        form = PermBookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            return redirect('perm-room-allotment')
    else:
        form = PermBookingForm(instance=booking)
    return render(request, 'room-book-perm.html', {'form': form})


@login_required
def perm_delete_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(PermanentBooking, id=booking_id)
        booking.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required()
def add_room(request):
    if request.method == 'POST':
        form = AddRoomForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('rooms')
    else:
        form = AddRoomForm()
    return render(request, 'add-room.html', {'form': form})


@login_required()
def edit_room(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        form = AddRoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            return redirect('rooms')
    else:
        form = AddRoomForm(instance=room)
    return render(request, 'add-room.html', {'form': form})


@csrf_exempt
def delete_room(request, room_id):
    if request.method == 'POST':
        try:
            room = Room.objects.get(id=room_id)
            room.delete()
            return JsonResponse({'success': True})
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Room not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
@csrf_exempt
def add_tenant(request):
    if request.method == 'POST':
        form = AddTenantForm(request.POST)
        if form.is_valid():
            tenant = form.save(commit=False)
            # Check if tenant exists in past tenants
            past_tenant = ArchivedTenant.objects.filter(name=tenant.name, contact=tenant.contact).first()
            if past_tenant:
                return JsonResponse({'exists': True, 'past_tenant_id': past_tenant.id})
            else:
                tenant.save()
                return JsonResponse({'exists': False})
        else:
            return JsonResponse({'errors': form.errors})
    else:
        form = AddTenantForm()
    return render(request, 'add-tenant.html', {'form': form})


# availability/views.py
@csrf_exempt
def confirm_add_tenant(request):
    if request.method == 'POST':
        past_tenant_id = request.POST.get('past_tenant_id')
        try:
            # Retrieve the past tenant
            past_tenant = ArchivedTenant.objects.get(id=past_tenant_id)

            # Create a new tenant with the same details
            tenant = Tenant.objects.create(
                name=past_tenant.name,
                contact=past_tenant.contact,
                email=past_tenant.email,
                address=past_tenant.address,
                gender=past_tenant.gender
            )

            # Delete the corresponding past tenant
            past_tenant.delete()

            return JsonResponse({'success': True})
        except ArchivedTenant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'ArchivedTenant does not exist'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


@login_required()
def edit_tenant(request, pk):
    tenant = get_object_or_404(Tenant, pk=pk)
    if request.method == 'POST':
        form = AddTenantForm(request.POST, instance=tenant)
        if form.is_valid():
            form.save()
            return redirect('occupants')
    else:
        form = AddTenantForm(instance=tenant)
    return render(request, 'add-tenant.html', {'form': form})


@csrf_exempt
def delete_tenant(request, tenant_id):
    if request.method == 'POST':
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            # Check if there are any bookings associated with the tenant
            if Booking.objects.filter(tenant=tenant).exists():
                return JsonResponse({'success': False, 'error': 'Cannot delete tenant with active bookings'})
            tenant.delete()
            return JsonResponse({'success': True})
        except Tenant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Tenant not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required()
def generate_pdf(request):
    # Fetch data from the PermBookings model
    rooms = Room.objects.all()
    permanent_bookings = PermanentBooking.objects.select_related('tenant').all()
    booking = PermanentBooking.objects.all().__len__()

    # Render the HTML content
    html_string = render_to_string('pdf_template.html',
                                   {
                                       'rooms': rooms,
                                       'permanent_bookings': permanent_bookings,
                                       'booking': booking,
                                       'user': request.user})

    # Create a WeasyPrint HTML object
    html = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri())

    # Generate the PDF
    pdf_file = html.write_pdf(stylesheets=[weasyprint.CSS(string='@page { size: A4; margin: 0; }')])

    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="permanent_allotment.pdf"'
    return response


@login_required()
def generate_temp_pdf(request):
    # Fetch data from the PermBookings model
    rooms = Room.objects.all()
    temporary_bookings = Booking.objects.select_related('tenant').all()

    booking = Booking.objects.all().__len__()

    # Render the HTML content
    html_string = render_to_string('pdf_temporary.html',
                                   {
                                       'rooms': rooms,
                                       'temporary_bookings': temporary_bookings,
                                       'booking': booking,
                                       'user': request.user})

    # Create a WeasyPrint HTML object
    html = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri())

    # Generate the PDF
    pdf_file = html.write_pdf(stylesheets=[weasyprint.CSS(string='@page { size: A4; margin: 0; }')])

    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="temporary-allotment.pdf"'
    return response


@login_required()
def generate_past_pdf(request):
    # Fetch data from the PermBookings model
    rooms = Room.objects.all()
    past_bookings = ArchivedBooking.objects.select_related('tenant').all()

    booking = ArchivedBooking.objects.all().__len__()

    # Render the HTML content
    html_string = render_to_string('pdf_past.html',
                                   {
                                       'rooms': rooms,
                                       'past_bookings': past_bookings,
                                       'booking': booking,
                                       'user': request.user})

    # Create a WeasyPrint HTML object
    html = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri())

    # Generate the PDF
    pdf_file = html.write_pdf(stylesheets=[weasyprint.CSS(string='@page { size: A4; margin: 0; }')])

    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="temporary-allotment.pdf"'
    return response


@login_required()
def generate_guest_pdf(request):
    # Fetch data from the PermBookings model
    rooms = Room.objects.all()
    tenants = Tenant.objects.all()
    temporary_bookings = Booking.objects.select_related('tenant').all()
    permanent_bookings = PermanentBooking.objects.select_related('tenant').all()
    guest = Tenant.objects.all().__len__()

    # Render the HTML content
    html_string = render_to_string('guest_pdf.html',
                                   {
                                       'rooms': rooms,
                                       'tenants': tenants,
                                       'guest': guest,
                                       'temporary_bookings': temporary_bookings,
                                       'permanent_bookings': permanent_bookings,
                                       'user': request.user})

    # Create a WeasyPrint HTML object
    html = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri())

    # Generate the PDF
    pdf_file = html.write_pdf(stylesheets=[weasyprint.CSS(string='@page { size: A4; margin: 0; }')])

    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="temporary-allotment.pdf"'
    return response


@login_required()
def generate_past_guest_pdf(request):
    # Fetch data from the PermBookings model
    rooms = Room.objects.all()
    tenants = ArchivedTenant.objects.all()
    archived_bookings = ArchivedBooking.objects.select_related('tenant').all()
    guest = ArchivedTenant.objects.all().__len__()

    # Render the HTML content
    html_string = render_to_string('guest_past_pdf.html',
                                   {
                                       'rooms': rooms,
                                       'tenants': tenants,
                                       'guest': guest,
                                       'archived_bookings': archived_bookings,
                                       'user': request.user})

    # Create a WeasyPrint HTML object
    html = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri())

    # Generate the PDF
    pdf_file = html.write_pdf(stylesheets=[weasyprint.CSS(string='@page { size: A4; margin: 0; }')])

    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="temporary-allotment.pdf"'
    return response


def run_delete_expired_bookings(request):
    call_command('delete_expired_bookings')
    return HttpResponse("Expired bookings archived and deleted successfully.")
