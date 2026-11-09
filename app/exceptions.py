import logging

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class NotFound(APIException):
    status_code = 404


class BookingConflict(APIException):
    status_code = 409


class DatabaseUnavailable(APIException):
    status_code = 503
    default_detail = "database unavailable"


def error_text(detail):
    if isinstance(detail, dict):
        return "; ".join(f"{field}: {error_text(errors)}" for field, errors in detail.items())
    if isinstance(detail, (list, tuple)):
        return "; ".join(error_text(error) for error in detail)
    return str(detail)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.error("unexpected request failure", exc_info=exc)
        return Response({"error": "internal server error"}, status=500)
    detail = (
        response.data.get("detail", response.data)
        if isinstance(response.data, dict)
        else response.data
    )
    message = error_text(detail).encode("utf-8", errors="backslashreplace").decode("utf-8")
    response.data = {"error": message}
    return response
