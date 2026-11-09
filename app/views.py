import logging

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.response import Response

from app import serializers
from app.db import Repository
from app.exceptions import DatabaseUnavailable

logger = logging.getLogger(__name__)


def get_repository() -> Repository:
    return Repository()


def validated(serializer_type, data):
    serializer = serializer_type(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


@extend_schema(request=serializers.RoomCreate, responses={201: serializers.CreatedRoom})
@api_view(["POST"])
def create_room(request):
    room = validated(serializers.RoomCreate, request.data)
    room_id = get_repository().create_room(room["description"], int(room["price"] * 100))
    return Response({"room_id": room_id}, status=201)


@extend_schema(request=serializers.RoomID, responses=serializers.Status)
@api_view(["POST"])
def delete_room(request):
    get_repository().delete_room(validated(serializers.RoomID, request.data)["room_id"])
    return Response({"status": "ok"})


@extend_schema(parameters=[serializers.RoomSort], responses=serializers.RoomResponse(many=True))
@api_view(["GET"])
def list_rooms(request):
    params = validated(serializers.RoomSort, request.query_params.dict())
    rooms = get_repository().list_rooms(params["sort_by"], params["order"])
    return Response(serializers.RoomResponse(rooms, many=True).data)


@extend_schema(request=serializers.BookingCreate, responses={201: serializers.CreatedBooking})
@api_view(["POST"])
def create_booking(request):
    booking = validated(serializers.BookingCreate, request.data)
    booking_id = get_repository().create_booking(
        booking["room_id"], booking["date_start"], booking["date_end"]
    )
    return Response({"cbooking_id": booking_id}, status=201)


@extend_schema(request=serializers.BookingID, responses=serializers.Status)
@api_view(["POST"])
def delete_booking(request):
    get_repository().delete_booking(validated(serializers.BookingID, request.data)["booking_id"])
    return Response({"status": "ok"})


@extend_schema(parameters=[serializers.RoomID], responses=serializers.BookingResponse(many=True))
@api_view(["GET"])
def list_bookings(request):
    params = validated(serializers.RoomID, request.query_params.dict())
    bookings = get_repository().list_bookings(params["room_id"])
    return Response(serializers.BookingResponse(bookings, many=True).data)


@extend_schema(responses=serializers.Status)
@api_view(["GET"])
def health(request):
    try:
        get_repository().ping()
    except Exception as exc:
        logger.warning("database health check failed", exc_info=exc)
        raise DatabaseUnavailable() from exc
    return Response({"status": "ok"})
