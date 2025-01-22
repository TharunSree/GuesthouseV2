# forms.py
import datetime

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Room, Booking, Tenant, PermanentBooking


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'}))


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['room', 'start_date', 'end_date', 'tenant', 'status']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(
                attrs={'class': 'form-control datepicker', 'type': 'text', 'data-provide': "datepicker",
                       'data-date-autoclose': "true", 'placeholder': "Check In",
                       'value': datetime.date.today().strftime('%Y-%m-%d')}),
            'end_date': forms.DateInput(
                attrs={'class': 'form-control datepicker', 'type': 'text', 'data-provide': "datepicker",
                       'data-date-autoclose': "true", 'placeholder': "Check Out",
                       'value': datetime.date.today().strftime('%Y-%m-%d')}),
            'tenant': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class PermBookingForm(forms.ModelForm):
    class Meta:
        model = PermanentBooking
        fields = ['room', 'tenant', 'start_date', 'end_date']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-control'}),
            'tenant': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(
                attrs={'class': 'form-control datepicker', 'type': 'text', 'data-provide': "datepicker",
                       'data-date-autoclose': "true", 'placeholder': "Check In",
                       'value': datetime.date.today().strftime('%Y-%m-%d')}),
        }


class AddRoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['number', 'status', 'room_type', 'ac_type', 'capacity']
        widgets = {
            'number': forms.TextInput(
                attrs={'type': "text", 'class': "form-control", 'id': "inputEmail3", 'placeholder': "Enter Room No."}),
            'status': forms.Select(choices=Room.ROOM_STATUS, attrs={'class': 'form-control'}),
            'room_type': forms.Select(choices=Room.ROOM_TYPE, attrs={'class': 'form-control'}),
            'ac_type': forms.Select(choices=Room.AC_TYPE, attrs={'class': 'form-control'}),
            'capacity': forms.TextInput(
                attrs={'type': "text", 'class': "form-control", 'id': "inputEmail3", 'placeholder': "Enter Capacity"})
        }


class AddTenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['name', 'contact', 'email', 'address', 'gender']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Enter Name"}),
            'contact': forms.TextInput(
                attrs={'class': 'form-control',
                       'placeholder': "Enter Mobile Number"}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': "Enter Email Address"}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': "Enter Address"}),
            'gender': forms.Select(choices=Tenant.GENDER_CHOICES, attrs={'class': 'form-control', }),
        }



