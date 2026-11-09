from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import connection, connections
from psycopg import connect, sql

from app.db import BookingConflict, NotFound

pytestmark = pytest.mark.integration


def create_room(client, description="room", price="100.00"):
    response = client.post("/rooms/create", data={"description": description, "price": price})
    assert response.status_code == 201, response.text
    return response.json()["room_id"]


def book(client, room_id, start, end):
    return client.post(
        "/bookings/create", data={"room_id": room_id, "date_start": start, "date_end": end}
    )


def test_full_http_lifecycle(integration_client, repository):
    client = integration_client
    assert client.get("/rooms/list").json() == []
    room_id = create_room(client, "Люкс", "1234.56")
    listing = client.get("/rooms/list").json()
    assert listing[0]["description"] == "Люкс"
    assert listing[0]["price"] == "1234.56"
    assert client.get("/bookings/list", params={"room_id": room_id}).json() == []
    later = book(client, room_id, "2026-06-25", "2026-06-27")
    earlier = book(client, room_id, "2026-06-20", "2026-06-25")
    assert later.status_code == earlier.status_code == 201
    assert book(client, room_id, "2026-06-23", "2026-06-27").status_code == 409
    rows = client.get("/bookings/list", params={"room_id": room_id}).json()
    assert rows == [
        {
            "booking_id": earlier.json()["cbooking_id"],
            "date_start": "2026-06-20",
            "date_end": "2026-06-25",
        },
        {
            "booking_id": later.json()["cbooking_id"],
            "date_start": "2026-06-25",
            "date_end": "2026-06-27",
        },
    ]
    earlier_id = earlier.json()["cbooking_id"]
    assert client.post("/bookings/delete", data={"booking_id": earlier_id}).status_code == 200
    assert client.post("/bookings/delete", data={"booking_id": earlier_id}).status_code == 404
    assert book(client, room_id, "2026-06-20", "2026-06-25").status_code == 201
    assert client.post("/rooms/delete", json={"room_id": room_id}).status_code == 200
    assert client.get("/bookings/list", params={"room_id": room_id}).status_code == 404
    assert book(client, room_id, "2026-06-20", "2026-06-25").status_code == 404
    assert client.post("/rooms/delete", json={"room_id": room_id}).status_code == 404
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM bookings")
        assert cursor.fetchone()[0] == 0


def test_all_sort_orders(integration_client):
    client = integration_client
    first = create_room(client, "first", "300.00")
    second = create_room(client, "second", "100.00")
    third = create_room(client, "third", "100.00")
    expected = {
        ("price", "asc"): [second, third, first],
        ("price", "desc"): [first, third, second],
        ("created_at", "asc"): [first, second, third],
        ("created_at", "desc"): [third, second, first],
    }
    for (sort_by, order), ids in expected.items():
        response = client.get("/rooms/list", params={"sort_by": sort_by, "order": order})
        assert response.status_code == 200
        assert [row["room_id"] for row in response.json()] == ids


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-06-20", "2026-06-25"),
        ("2026-06-21", "2026-06-24"),
        ("2026-06-19", "2026-06-26"),
        ("2026-06-18", "2026-06-21"),
        ("2026-06-24", "2026-06-28"),
    ],
)
def test_all_overlap_shapes(integration_client, start, end):
    client = integration_client
    room_id = create_room(client)
    assert book(client, room_id, "2026-06-20", "2026-06-25").status_code == 201
    assert book(client, room_id, start, end).status_code == 409
    other_room = create_room(client)
    assert book(client, other_room, start, end).status_code == 201


def test_adjacent_intervals_on_both_sides(integration_client):
    client = integration_client
    room_id = create_room(client)
    assert book(client, room_id, "2026-06-20", "2026-06-25").status_code == 201
    assert book(client, room_id, "2026-06-18", "2026-06-20").status_code == 201
    assert book(client, room_id, "2026-06-25", "2026-06-28").status_code == 201


def test_concurrent_booking_is_atomic(repository):
    room_id = repository.create_room("concurrent room", 10000)
    barrier = Barrier(8)

    def attempt(_):
        barrier.wait(timeout=10)
        try:
            repository.create_booking(room_id, date(2026, 6, 20), date(2026, 6, 25))
            return "created"
        except BookingConflict:
            return "conflict"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(attempt, range(8)))
    assert results.count("created") == 1
    assert results.count("conflict") == 7
    assert len(repository.list_bookings(room_id)) == 1


def test_commit_survives_new_connection(repository, test_database_config):
    room_id = repository.create_room("persistent", 1)
    booking_id = repository.create_booking(room_id, date(2024, 2, 29), date(2024, 3, 1))
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_schema()")
        schema = cursor.fetchone()[0]
    _, dsn = test_database_config
    with connect(dsn) as conn:
        row = conn.execute(
            sql.SQL("SELECT id FROM {}.bookings WHERE room_id = %s").format(sql.Identifier(schema)),
            (room_id,),
        ).fetchone()
    assert row[0] == booking_id


def test_missing_room(repository):
    with pytest.raises(NotFound):
        repository.list_bookings(999999)
    with pytest.raises(NotFound):
        repository.create_booking(999999, date(2026, 1, 1), date(2026, 1, 2))
