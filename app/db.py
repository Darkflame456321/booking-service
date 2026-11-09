from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.models import F

from app.exceptions import BookingConflict, NotFound
from app.models import Booking, Room


class Repository:
    def ping(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

    def create_room(self, description: str, price_cents: int) -> int:
        return Room.objects.create(description=description, price_cents=price_cents).pk

    def delete_room(self, room_id: int) -> None:
        with transaction.atomic():
            count, _ = Room.objects.filter(pk=room_id).delete()
            if not count:
                raise NotFound("room not found")

    def list_rooms(self, sort_by: str, order: str) -> list[Room]:
        columns = {"price": "price_cents", "created_at": "created_at"}
        if sort_by not in columns or order not in {"asc", "desc"}:
            raise ValueError("invalid sort")
        prefix = "-" if order == "desc" else ""
        return list(Room.objects.order_by(prefix + columns[sort_by], prefix + "id"))

    def create_booking(self, room_id: int, date_start: date, date_end: date) -> int:
        try:
            with transaction.atomic():
                return Booking.objects.create(
                    room_id=room_id, date_start=date_start, date_end=date_end
                ).pk
        except IntegrityError as exc:
            code = getattr(exc.__cause__, "sqlstate", None)
            if code == "23503":
                raise NotFound("room not found") from exc
            if code == "23P01":
                raise BookingConflict("room is already booked for these dates") from exc
            raise

    def delete_booking(self, booking_id: int) -> None:
        count, _ = Booking.objects.filter(pk=booking_id).delete()
        if not count:
            raise NotFound("booking not found")

    def list_bookings(self, room_id: int) -> list[dict]:
        rows = list(
            Room.objects.filter(pk=room_id)
            .order_by("bookings__date_start", "bookings__id")
            .values(
                booking_id=F("bookings__id"),
                date_start=F("bookings__date_start"),
                date_end=F("bookings__date_end"),
            )
        )
        if not rows:
            raise NotFound("room not found")
        return [row for row in rows if row["booking_id"] is not None]
