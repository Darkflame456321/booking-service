from django.core.exceptions import DisallowedHost
from django.http import JsonResponse


class JSONErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            request.get_host()
        except DisallowedHost:
            return JsonResponse({"error": "invalid Host header"}, status=400)
        return self.get_response(request)


def not_found(request, exception):
    return JsonResponse({"error": "endpoint not found"}, status=404)


def bad_request(request, exception):
    return JsonResponse({"error": "invalid request"}, status=400)


def server_error(request):
    return JsonResponse({"error": "internal server error"}, status=500)
