# middleware.py
from django.shortcuts import redirect
from django.urls import reverse


class RedirectGuestHomeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.path == reverse('index'):
            return redirect(reverse('room-allotment'))
        response = self.get_response(request)
        return response
