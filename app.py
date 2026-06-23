from __future__ import annotations

import sqlite3
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from moderation import normalize_text


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "pinmap.db"
DATABASE_URL = os.environ.get("DATABASE_URL")
ALLOWED_PIN_FIELDS = {"name", "origin", "lat", "lng", "message"}
BLOCKED_ORIGIN_TERMS = {
    "spam",
    "golpe",
    "fraude",
    "scam",
    "phishing",
    "idiota",
    "ameaca",
    "matar",
}
URL_PATTERN = re.compile(r"(https?://|www\\.|\\.com\\b|\\.net\\b|\\.org\\b)", re.IGNORECASE)
MAX_POSTS_PER_WINDOW = 30
RATE_LIMIT_WINDOW_SECONDS = 60
POST_TIMESTAMPS_BY_IP: dict[str, list[float]] = {}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2048


def get_connection() -> Any:
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        if DATABASE_URL:
            connection.execute(
                """
                create table if not exists pins (
                    id bigserial primary key,
                    name text not null,
                    origin text not null,
                    message text not null default '',
                    lat double precision not null,
                    lng double precision not null,
                    is_approved boolean not null default true,
                    created_at timestamptz not null default now()
                )
                """
            )
            connection.execute(
                """
                create table if not exists visits (
                    id bigserial primary key,
                    created_at timestamptz not null default now()
                )
                """
            )
        else:
            connection.execute(
                """
                create table if not exists pins (
                    id integer primary key autoincrement,
                    name text not null,
                    origin text not null,
                    message text not null,
                    lat real not null,
                    lng real not null,
                    is_approved integer not null default 1,
                    created_at text not null default current_timestamp
                )
                """
            )
            connection.execute(
                """
                create table if not exists visits (
                    id integer primary key autoincrement,
                    created_at text not null default current_timestamp
                )
                """
            )
        connection.execute(
            "create index if not exists idx_pins_approved_created on pins (is_approved, created_at desc)"
        )


def param_placeholder() -> str:
    return "%s" if DATABASE_URL else "?"


def approved_condition() -> str:
    return "is_approved = true" if DATABASE_URL else "is_approved = 1"


def record_visit() -> None:
    with get_connection() as connection:
        connection.execute(
            f"insert into visits (created_at) values ({param_placeholder()})",
            (datetime.now(timezone.utc).isoformat(),),
        )


def count_visits() -> int:
    with get_connection() as connection:
        row = connection.execute("select count(*) as total from visits").fetchone()

    return int(row["total"])


def row_to_pin(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "origin": row["origin"],
        "message": row["message"],
        "lat": row["lat"],
        "lng": row["lng"],
        "isApproved": bool(row["is_approved"]),
        "createdAt": str(row["created_at"]),
    }


def clean_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback

    return str(value).strip()


def contains_html(value: str) -> bool:
    return "<" in value or ">" in value


def get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    return request.remote_addr or "unknown"


def is_rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    timestamps = POST_TIMESTAMPS_BY_IP.setdefault(client_ip, [])
    recent_timestamps = [
        timestamp
        for timestamp in timestamps
        if now - timestamp < RATE_LIMIT_WINDOW_SECONDS
    ]
    POST_TIMESTAMPS_BY_IP[client_ip] = recent_timestamps

    if len(recent_timestamps) >= MAX_POSTS_PER_WINDOW:
        return True

    recent_timestamps.append(now)
    return False


def parse_coordinate(value: Any, field_name: str, minimum: float, maximum: float) -> tuple[float | None, str | None]:
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None, f"{field_name} deve ser um numero valido."

    if coordinate < minimum or coordinate > maximum:
        return None, f"{field_name} deve estar entre {minimum} e {maximum}."

    return coordinate, None


def is_blocked_origin(origin: str) -> bool:
    normalized_origin = normalize_text(origin)
    return any(term in normalized_origin for term in BLOCKED_ORIGIN_TERMS)


def validate_pin(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None, str | None]:
    unexpected_fields = set(payload) - ALLOWED_PIN_FIELDS
    if unexpected_fields:
        return None, "invalid_origin", "Campos nao permitidos no payload."

    name = clean_text(payload.get("name"), "Visitante anonimo") or "Visitante anonimo"
    origin = clean_text(payload.get("origin"))
    message = ""

    if len(name) > 40:
        return None, "invalid_origin", "name deve ter no maximo 40 caracteres."

    if contains_html(name):
        return None, "invalid_origin", "name nao pode conter HTML."

    if not origin:
        return None, "invalid_origin", "origin e obrigatorio."

    if len(origin) > 80:
        return None, "invalid_origin", "origin deve ter no maximo 80 caracteres."

    if contains_html(origin):
        return None, "blocked_origin", "origin nao pode conter HTML."

    if URL_PATTERN.search(origin):
        return None, "blocked_origin", "origin nao pode conter URL."

    if is_blocked_origin(origin):
        return None, "blocked_origin", "origin bloqueada pela moderacao."

    lat, lat_error = parse_coordinate(payload.get("lat"), "lat", -90, 90)
    if lat_error:
        return None, "invalid_coordinates", lat_error

    lng, lng_error = parse_coordinate(payload.get("lng"), "lng", -180, 180)
    if lng_error:
        return None, "invalid_coordinates", lng_error

    return {
        "name": name,
        "origin": origin,
        "message": message,
        "lat": lat,
        "lng": lng,
    }, None, None


@app.get("/")
@app.get("/index.html")
def index() -> Any:
    record_visit()
    return render_template("index.html")


@app.get("/api/visits")
def get_visits() -> Any:
    return jsonify({"visits": count_visits()})


@app.get("/api/pins")
def get_pins() -> Any:
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            select id, name, origin, message, lat, lng, is_approved, created_at
            from pins
            where {approved_condition()}
            order by created_at desc
            limit 250
            """
        ).fetchall()

    return jsonify([row_to_pin(row) for row in rows])


@app.post("/api/pins")
def create_pin() -> Any:
    if is_rate_limited(get_client_ip()):
        return jsonify({"error": "Muitas tentativas. Aguarde um pouco."}), 429

    if not request.is_json:
        return jsonify({"error": "Content-Type deve ser application/json."}), 400

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON invalido."}), 400

    pin, error_code, error = validate_pin(payload)

    if error:
        return jsonify({"code": error_code, "error": error}), 400

    with get_connection() as connection:
        created_at = datetime.now(timezone.utc).isoformat()
        placeholder = param_placeholder()

        if DATABASE_URL:
            row = connection.execute(
                f"""
                insert into pins (name, origin, message, lat, lng, is_approved, created_at)
                values ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, true, {placeholder})
                returning id, name, origin, message, lat, lng, is_approved, created_at
                """,
                (
                    pin["name"],
                    pin["origin"],
                    pin["message"],
                    pin["lat"],
                    pin["lng"],
                    created_at,
                ),
            ).fetchone()
        else:
            cursor = connection.execute(
                """
                insert into pins (name, origin, message, lat, lng, is_approved, created_at)
                values (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    pin["name"],
                    pin["origin"],
                    pin["message"],
                    pin["lat"],
                    pin["lng"],
                    created_at,
                ),
            )
            row = connection.execute(
                """
                select id, name, origin, message, lat, lng, is_approved, created_at
                from pins
                where id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

    return jsonify(row_to_pin(row)), 201


init_db()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG") == "1"
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug)
