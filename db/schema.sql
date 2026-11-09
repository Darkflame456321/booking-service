CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;

CREATE TABLE rooms (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    description TEXT NOT NULL CHECK (length(btrim(description)) BETWEEN 1 AND 10000),
    price_cents BIGINT NOT NULL CHECK (price_cents BETWEEN 1 AND 999999999999),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX rooms_price_id_idx ON rooms (price_cents, id);
CREATE INDEX rooms_created_at_id_idx ON rooms (created_at, id);

CREATE TABLE bookings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id BIGINT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    date_start DATE NOT NULL CHECK (date_start BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
    date_end DATE NOT NULL CHECK (date_end BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
    CHECK (date_end > date_start),
    CONSTRAINT bookings_no_overlap EXCLUDE USING gist (
        room_id WITH =,
        daterange(date_start, date_end, '[)') WITH &&
    )
);

CREATE INDEX bookings_room_start_id_idx ON bookings (room_id, date_start, id);
