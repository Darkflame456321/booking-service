import re
from datetime import date
from decimal import Decimal

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"body": "body must be an object"})
        unknown = data.keys() - self.fields.keys()
        if unknown:
            raise serializers.ValidationError(
                {"body": "unknown fields: " + ", ".join(sorted(unknown))}
            )
        return super().to_internal_value(data)


class PositiveIDField(serializers.IntegerField):
    def __init__(self, **kwargs):
        super().__init__(min_value=1, max_value=9223372036854775807, **kwargs)

    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (int, str)):
            self.fail("invalid")
        if not re.fullmatch(r"[0-9]{1,19}", str(data)):
            self.fail("invalid")
        return super().to_internal_value(data)


class CalendarDateField(serializers.DateField):
    def to_internal_value(self, data):
        if not isinstance(data, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", data):
            raise serializers.ValidationError("date must be in YYYY-MM-DD format")
        try:
            return date.fromisoformat(data)
        except ValueError as exc:
            raise serializers.ValidationError("invalid calendar date") from exc


class DescriptionField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        if any(0xD800 <= ord(c) <= 0xDFFF for c in data):
            raise serializers.ValidationError("description contains invalid characters")
        return super().to_internal_value(data)


class RoomCreate(StrictSerializer):
    description = DescriptionField(min_length=1, max_length=10000)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class RoomID(StrictSerializer):
    room_id = PositiveIDField()


class BookingID(StrictSerializer):
    booking_id = PositiveIDField()


class BookingCreate(RoomID):
    date_start = CalendarDateField()
    date_end = CalendarDateField()

    def validate(self, attrs):
        if attrs["date_end"] <= attrs["date_start"]:
            raise serializers.ValidationError("date_end must be after date_start")
        return attrs


class RoomSort(StrictSerializer):
    sort_by = serializers.ChoiceField(choices=["price", "created_at"], default="created_at")
    order = serializers.ChoiceField(choices=["asc", "desc"], default="asc")


class RoomResponse(serializers.Serializer):
    room_id = serializers.IntegerField(source="id")
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    created_at = serializers.DateTimeField()


class BookingResponse(serializers.Serializer):
    booking_id = serializers.IntegerField()
    date_start = serializers.DateField()
    date_end = serializers.DateField()


class CreatedRoom(serializers.Serializer):
    room_id = serializers.IntegerField()


class CreatedBooking(serializers.Serializer):
    cbooking_id = serializers.IntegerField()


class Status(serializers.Serializer):
    status = serializers.CharField()
