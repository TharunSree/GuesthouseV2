# availability/views.py
from calendar import HTMLCalendar, monthrange

import weasyprint
from django.db import IntegrityError
from django.db.models import IntegerField
from django.db.models.functions import Cast
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from datetime import date as dt, timedelta, datetime
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from .models import Room, Booking, PermanentBooking, Tenant, ArchivedBooking, ArchivedTenant
from django.contrib.auth.decorators import login_required
from .forms import BookingForm, PermBookingForm, AddRoomForm, AddTenantForm
from django.core.management import call_command


def index(request):
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
    bookings = Booking.objects.all()
    permanent_bookings = PermanentBooking.objects.all()
    selected_month = int(request.GET.get('month', datetime.now().month))
    selected_year = int(request.GET.get('year', datetime.now().year))
    num_days = monthrange(selected_year, selected_month)[1]

    # Generate the list of dates for the selected month and year
    dates = [datetime(selected_year, selected_month, day) for day in range(1, num_days + 1)]

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
        'months': {
            1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
            7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
        },
        'years': [datetime.now().year, datetime.now().year - 1, datetime.now().year + 1],
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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


def available_rooms(request):
    # Parse the start and end dates from the request or use the current date
    start_date_str = request.GET.get('start_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date_str = request.GET.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
    rooms_with_free_slots = []

    for room in rooms:
        # Check the number of temporary bookings for the room within the given date range
        temporary_bookings_count = Booking.objects.filter(
            room=room,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).count()

        # Check the number of permanent bookings
        permanent_bookings_count = PermanentBooking.objects.filter(room=room).count()

        # Calculate total bookings and available slots
        current_bookings_count = temporary_bookings_count + permanent_bookings_count
        free_slots = room.capacity - current_bookings_count

        # Add room to the list if at least one slot is available
        if free_slots > 0:
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

            # Add the room with relevant details to the result list
            rooms_with_free_slots.append({
                'room': room,
                'free_slots': free_slots,
                'statuses': list(statuses),
            })
    rooms_with_free_slots = sorted(rooms_with_free_slots,
                                   key=lambda x: int(''.join(filter(str.isdigit, x['room'].number))))
    context = {
        'rooms_with_free_slots': rooms_with_free_slots,
    }
    return render(request, 'available-rooms.html', context)


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

            # Do not delete the corresponding archived tenant
            # archived_tenant.delete()

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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
    past_bookings = ArchivedBooking.objects.select_related('tenant').all()
    bookings = ArchivedBooking.objects.all().__len__()

    context = {
        'rooms': rooms,
        'past_bookings': past_bookings,
        'bookings': bookings,
    }
    return render(request, 'past-bookings.html', context)


@login_required
def room_history(request):
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')

    selected_room = request.GET.get('room', None)
    past_bookings = ArchivedBooking.objects.filter(room__number=selected_room).select_related('tenant')
    temporary_bookings = Booking.objects.filter(room__number=selected_room).select_related('tenant')
    permanent_bookings = PermanentBooking.objects.filter(room__number=selected_room).select_related('tenant')
    bookings = past_bookings.count() + temporary_bookings.count() + permanent_bookings.count()

    context = {
        'rooms': rooms,
        'past_bookings': past_bookings,
        'bookings': bookings,
        'selected_room': selected_room,
        'temporary_bookings': temporary_bookings,  # Add temporary bookings to context
        'permanent_bookings': permanent_bookings,  # Add permanent bookings to context
    }
    return render(request, 'room-history.html', context)


@login_required
def occupants(request):
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
    # Get the list of rooms, bookings, permanent bookings, and past bookings (archived)
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
    bookings = Booking.objects.all()
    permanent_bookings = PermanentBooking.objects.all()
    archived_bookings = ArchivedBooking.objects.all()

    # Get the selected month and year from the GET parameters, or default to the current month and year
    try:
        selected_month = int(request.GET.get('month', datetime.now().month))
        selected_year = int(request.GET.get('year', datetime.now().year))
    except ValueError:
        selected_month = datetime.now().month
        selected_year = datetime.now().year

    selected_room = request.GET.get('room', None)

    # Get the first and last day of the selected month
    first_day = datetime(selected_year, selected_month, 1)
    last_day = datetime(selected_year, selected_month + 1, 1) - timedelta(days=1)

    # Get the weekday of the first day of the month (0=Monday, 6=Sunday)
    first_day_weekday = first_day.weekday()  # 0 for Monday, 6 for Sunday

    # Generate list of all days in the selected month
    days_in_month = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]

    # Create a list for the calendar, including only the days of the selected month
    days_in_calendar = []

    # Pre-fill the previous month's days to align the start of the first week properly
    if first_day_weekday > 0:  # If the first day is not Monday, we need to fill days from the previous month
        prev_month_last_day = first_day - timedelta(days=1)
        prev_month_days = [prev_month_last_day - timedelta(days=i) for i in range(first_day_weekday)]
        days_in_calendar.extend(reversed(prev_month_days))  # Add days from previous month (only for alignment)

    # Add current month days (from first day to last day)
    days_in_calendar.extend(days_in_month)

    # Fill in the next month's days only if the last week isn't full (this ensures calendar completeness)
    while len(days_in_calendar) % 7 != 0:
        next_month_day = last_day + timedelta(days=1)
        days_in_calendar.append(next_month_day)
        last_day = next_month_day

    # Group the days into weeks (7 days per week)
    weeks = [days_in_calendar[i:i + 7] for i in range(0, len(days_in_calendar), 7)]

    # Initialize the availability dictionary, now considering capacity
    availability = {
        room.number: {day.day: ['Available'] * room.capacity for day in days_in_month}
        for room in rooms
    }

    # Update availability based on temporary bookings
    for booking in bookings:
        for date in days_in_month:
            if booking.start_date <= date.date() <= booking.end_date:
                # Find the first available spot for the room on this date
                room_availability = availability[booking.room.number][date.day]
                for i in range(len(room_availability)):
                    if room_availability[i] == 'Available':
                        room_availability[i] = 'Booked'
                        break

    # Update availability based on permanent bookings
    for permanent_booking in permanent_bookings:
        end_date = datetime.max.date() if permanent_booking.end_date is None else permanent_booking.end_date
        for date in days_in_month:
            if permanent_booking.start_date <= date.date() <= end_date:
                # Find the first available spot for the room on this date
                room_availability = availability[permanent_booking.room.number][date.day]
                for i in range(len(room_availability)):
                    if room_availability[i] == 'Available':
                        room_availability[i] = 'Permanent'
                        break

    # Update availability based on archived/past bookings (those before today)
    for archived_booking in archived_bookings:
        for date in days_in_month:
            if archived_booking.checkin_date <= date.date() <= archived_booking.checkout_date:
                # Find the first available spot for the room on this date
                room_availability = availability[archived_booking.room.number][date.day]
                for i in range(len(room_availability)):
                    if room_availability[i] == 'Available':
                        room_availability[i] = 'Booked'  # Treat archived bookings as "Booked"
                        break

    # Add to context the data needed for the template
    context = {
        'rooms': rooms,
        'weeks': weeks,
        'availability': availability,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_room': selected_room,
        'months': {
            1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
            7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
        },
        'years': [datetime.now().year, datetime.now().year - 1, datetime.now().year + 1],
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
        try:
            archived_tenant, created = ArchivedTenant.objects.get_or_create(
                name=booking.tenant.name,
                contact=booking.tenant.contact,
                email=booking.tenant.email,
                defaults={
                    'booking_id': booking.id,
                    'address': booking.tenant.address,
                    'gender': booking.tenant.gender,
                }
            )
            archived_booking = ArchivedBooking(
                booking_id=booking.id,
                room=booking.room,
                tenant=archived_tenant,
                checkin_date=str(booking.start_date),
                checkout_date=str(booking.end_date),
                status='deleted',
                type='temporary'
            )
            archived_booking.save()
            if not ArchivedTenant.objects.filter(name=booking.tenant.name, contact=booking.tenant.contact,
                                                 email=booking.tenant.email).exists():
                booking.tenant.delete()
            booking.delete()
            return JsonResponse({'success': True})
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'Duplicate entry for ArchivedTenant'}, status=400)
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
        try:
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
                checkout_date=dt.today(),
                status='deleted',
                type='permanent'
            )
            archived_booking.save()
            # Check if the tenant is already in ArchivedTenant
            if not ArchivedTenant.objects.filter(name=booking.tenant.name, contact=booking.tenant.contact,
                                                 email=booking.tenant.email).exists():
                booking.tenant.delete()
            booking.delete()
            return JsonResponse({'success': True})
        except IntegrityError:
            return JsonResponse({'success': False, 'error': 'Duplicate entry for ArchivedTenant'}, status=400)
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
def generate_room_history_pdf(request, selected_room):
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')

    past_bookings = ArchivedBooking.objects.filter(room__number=selected_room).select_related('tenant')
    temporary_bookings = Booking.objects.filter(room__number=selected_room).select_related('tenant')
    permanent_bookings = PermanentBooking.objects.filter(room__number=selected_room).select_related('tenant')
    total_bookings = list(past_bookings) + list(temporary_bookings) + list(permanent_bookings)
    bookings = past_bookings.count() + temporary_bookings.count() + permanent_bookings.count()

    # Render the HTML content
    html_string = render_to_string('room_history_pdf.html',
                                   {
                                       'rooms': rooms,
                                       'past_bookings': total_bookings,
                                       'bookings': bookings,
                                       'selected_room': selected_room,
                                       'user': request.user})

    # Create a WeasyPrint HTML object
    html = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri())
    # Generate the PDF
    pdf_file = html.write_pdf(stylesheets=[weasyprint.CSS(string='@page { size: A4; margin: 0; }')])

    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'filename="room-history.pdf"'
    return response


@login_required()
def generate_guest_pdf(request):
    # Fetch data from the PermBookings model
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
    rooms = Room.objects.annotate(
        number_as_int=Cast('number', IntegerField())
    ).order_by('number_as_int', 'number')
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
