from django.urls import resolve


def current_path(request):
    current_url = resolve(request.path_info).url_name
    return {'current_url': current_url}
