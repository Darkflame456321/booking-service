from datetime import date
from decimal import Decimal

import pytest

from app.db import BookingConflict, NotFound
from app.parsers import MAX_BODY_BYTES


def assert_error(response, status):
    assert response.status_code == status, response.text
    assert response.headers["content-type"] == "application/json"
    assert isinstance(response.json()["error"], str)


@pytest.mark.parametrize("encoding", ["json", "data"])
def test_create_room_accepts_json_and_form(client, repository_mock, encoding):
    repository_mock.create_room.return_value = 24
    response = client.post(
        "/rooms/create", **{encoding: {"description": "  Люкс  ", "price": "1234.56"}}
    )
    assert response.status_code == 201
    assert response.json() == {"room_id": 24}
    repository_mock.create_room.assert_called_once_with("Люкс", 123456)


@pytest.mark.parametrize("price", [0, -1, "NaN", "Infinity", "1.001", True, [], "1e100"])
def test_invalid_price_does_not_write(client, repository_mock, price):
    response = client.post("/rooms/create", json={"description": "room", "price": price})
    assert_error(response, 400)
    repository_mock.create_room.assert_not_called()


@pytest.mark.parametrize("description", ["", "   ", "x" * 10001, "bad\x00text", 5, None])
def test_invalid_description(client, repository_mock, description):
    assert_error(client.post("/rooms/create", json={"description": description, "price": 1}), 400)
    repository_mock.create_room.assert_not_called()


@pytest.mark.parametrize("price,cents", [("0.01", 1), ("9999999999.99", 999999999999)])
def test_price_boundaries(client, repository_mock, price, cents):
    repository_mock.create_room.return_value = 1
    assert (
        client.post("/rooms/create", json={"description": "room", "price": price}).status_code
        == 201
    )
    repository_mock.create_room.assert_called_once_with("room", cents)


def test_json_decimal_is_not_rounded_through_float(client, repository_mock):
    repository_mock.create_room.return_value = 1
    response = client.post(
        "/rooms/create",
        content='{"description":"room","price":9999999999.99}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 201
    repository_mock.create_room.assert_called_once_with("room", 999999999999)


@pytest.mark.parametrize(
    "exponent", ["999999999999999999999999999", "-999999999999999999999999999"]
)
def test_unrepresentable_json_decimal_returns_client_error(client, repository_mock, exponent):
    response = client.post(
        "/rooms/create",
        content='{"description":"room","price":1e' + exponent + "}",
        headers={"Content-Type": "application/json"},
    )
    assert_error(response, 400)
    repository_mock.create_room.assert_not_called()


def test_validation_errors_are_plain_text_with_field_names(client, repository_mock):
    response = client.post("/rooms/create", json={"description": "", "price": -1})
    assert_error(response, 400)
    message = response.json()["error"]
    assert "description: This field may not be blank." in message
    assert "price: Ensure this value is greater than or equal to 0.01." in message
    assert "ErrorDetail" not in message
    repository_mock.create_room.assert_not_called()


def test_invalid_unicode_field_name_returns_json_error(client, repository_mock):
    response = client.post(
        "/rooms/create",
        content='{"description":"room","price":1,"\\ud800":2}',
        headers={"Content-Type": "application/json"},
    )
    assert_error(response, 400)
    assert "\\ud800" in response.json()["error"]
    assert "ErrorDetail" not in response.json()["error"]
    repository_mock.create_room.assert_not_called()


@pytest.mark.parametrize("host", ["unexpected.example", "localhost", "bad host"])
def test_disallowed_host_is_rejected_before_handler(client, repository_mock, settings, host):
    settings.ALLOWED_HOSTS = ["booking.example"]
    response = client.get("/rooms/list", headers={"Host": host})
    assert_error(response, 400)
    repository_mock.list_rooms.assert_not_called()


@pytest.mark.parametrize("host", ["booking.example", "booking.example:9000", "BOOKING.EXAMPLE"])
def test_configured_host_is_accepted(client, repository_mock, settings, host):
    settings.ALLOWED_HOSTS = ["booking.example"]
    repository_mock.list_rooms.return_value = []
    response = client.get("/rooms/list", headers={"Host": host})
    assert response.status_code == 200
    assert response.json() == []
    repository_mock.list_rooms.assert_called_once_with("created_at", "asc")


@pytest.mark.parametrize("encoding", ["json", "data"])
def test_create_booking(client, repository_mock, encoding):
    repository_mock.create_booking.return_value = 1444
    response = client.post(
        "/bookings/create",
        **{encoding: {"room_id": "24", "date_start": "2024-02-29", "date_end": "2024-03-01"}},
    )
    assert response.status_code == 201
    assert response.json() == {"cbooking_id": 1444}
    repository_mock.create_booking.assert_called_once_with(24, date(2024, 2, 29), date(2024, 3, 1))


@pytest.mark.parametrize(
    "start,end",
    [
        ("2023-02-29", "2023-03-01"),
        ("2024-04-31", "2024-05-02"),
        ("2024-2-01", "2024-03-01"),
        ("2024-02-01T00:00:00", "2024-03-01"),
        ("0000-01-01", "2024-01-01"),
        ("2024-01-02", "2024-01-02"),
        ("2024-01-03", "2024-01-02"),
        (1704067200, "2024-01-02"),
        (None, "2024-01-02"),
    ],
)
def test_invalid_booking_dates(client, repository_mock, start, end):
    response = client.post(
        "/bookings/create", json={"room_id": 1, "date_start": start, "date_end": end}
    )
    assert_error(response, 400)
    repository_mock.create_booking.assert_not_called()


@pytest.mark.parametrize("room_id", [0, -1, True, 1.5, "1.0", "9223372036854775808", "１"])
def test_invalid_id(client, repository_mock, room_id):
    assert_error(client.post("/rooms/delete", json={"room_id": room_id}), 400)
    repository_mock.delete_room.assert_not_called()


@pytest.mark.parametrize("sort_by", ["price", "created_at"])
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_room_sort_parameters(client, repository_mock, sort_by, order):
    repository_mock.list_rooms.return_value = []
    response = client.get("/rooms/list", params={"sort_by": sort_by, "order": order})
    assert response.json() == []
    repository_mock.list_rooms.assert_called_once_with(sort_by, order)


def test_default_sort_and_decimal_response(client, repository_mock):
    repository_mock.list_rooms.return_value = [
        {
            "id": 1,
            "description": "room",
            "price": Decimal("0.10"),
            "created_at": "2026-11-08T12:00:00Z",
        }
    ]
    response = client.get("/rooms/list")
    assert response.status_code == 200
    assert response.json()[0]["price"] == "0.10"
    repository_mock.list_rooms.assert_called_once_with("created_at", "asc")


@pytest.mark.parametrize("params", [{"sort_by": "id"}, {"order": "drop table rooms"}])
def test_invalid_sort(client, repository_mock, params):
    assert_error(client.get("/rooms/list", params=params), 400)
    repository_mock.list_rooms.assert_not_called()


@pytest.mark.parametrize("url", ["/bookings/list", "/bookings/list?room_id=-1"])
def test_invalid_list_room_id(client, url):
    assert_error(client.get(url), 400)


@pytest.mark.parametrize("body", ["{", "[]", "null", '{"price":1,"price":2}', '{"price":1} {}'])
def test_malformed_json(client, body):
    assert_error(
        client.post("/rooms/create", content=body, headers={"Content-Type": "application/json"}),
        400,
    )


def test_body_limits_and_media_type(client):
    assert_error(client.post("/rooms/create", content="text"), 415)
    assert_error(
        client.post(
            "/rooms/create",
            content="x" * (MAX_BODY_BYTES + 1),
            headers={"Content-Type": "application/json"},
        ),
        413,
    )
    assert_error(client.post("/rooms/create", json={"description": "r", "price": 1, "x": 2}), 400)
    assert_error(
        client.post(
            "/rooms/create",
            content="description=r&price=1&price=2",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ),
        400,
    )


def test_json_for_unknown_route_and_wrong_method(client):
    assert_error(client.get("/unknown"), 404)
    response = client.get("/rooms/create")
    assert_error(response, 405)
    assert "POST" in response.headers["allow"]


@pytest.mark.parametrize(
    "error,status",
    [
        (NotFound("room not found"), 404),
        (BookingConflict("conflict"), 409),
        (RuntimeError("secret database password"), 500),
    ],
)
def test_storage_errors(client, repository_mock, error, status):
    repository_mock.create_booking.side_effect = error
    response = client.post(
        "/bookings/create",
        json={"room_id": 1, "date_start": "2026-01-01", "date_end": "2026-01-02"},
    )
    assert_error(response, status)
    assert "secret" not in response.text


def test_health(client, repository_mock):
    assert client.get("/healthz").json() == {"status": "ok"}
    repository_mock.ping.side_effect = RuntimeError("offline")
    assert_error(client.get("/healthz"), 503)
