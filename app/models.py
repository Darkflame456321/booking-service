from decimal import Decimal

from django.db import models
from django.db.models.functions import Now


class Room(models.Model):
    description = models.TextField()
    price_cents = models.BigIntegerField()
    created_at = models.DateTimeField(db_default=Now())

    @property
    def price(self) -> Decimal:
        return Decimal(self.price_cents) / 100

    class Meta:
        db_table = "rooms"
        managed = False
        ordering = ["created_at", "id"]


class Booking(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    date_start = models.DateField()
    date_end = models.DateField()

    class Meta:
        db_table = "bookings"
        managed = False
        ordering = ["date_start", "id"]
