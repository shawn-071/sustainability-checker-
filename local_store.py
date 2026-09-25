"""Small local SQLite store for CropWise accounts, history, and field cache.

Passwords are stored as salted PBKDF2 hashes. Uploaded photos are never saved.
For hosted deployments, configure persistent storage before relying on history.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(os.environ.get("CROPWISE_DB_PATH", Path(__file__).with_name("cropwise.db")))
PBKDF2_ROUNDS = 310_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE,
                created_at TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                crop TEXT,
                outcome TEXT,
                score REAL,
                details_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(username) REFERENCES users(username)
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS location_cache (
                cache_key TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                data_json TEXT NOT NULL
            )"""
        )


def create_user(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not USERNAME_RE.fullmatch(username):
        return False, "Use 3–32 letters, numbers, or underscores for the username."
    if len(password) < 10:
        return False, "Use a password with at least 10 characters."

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    try:
        with _connect() as db:
            db.execute(
                "INSERT INTO users(username, salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username, salt.hex(), password_hash.hex(), _now()),
            )
    except sqlite3.IntegrityError:
        return False, "That username already exists."
    return True, "Account created. You can sign in now."


def authenticate(username: str, password: str) -> bool:
    with _connect() as db:
        row = db.execute(
            "SELECT salt, password_hash FROM users WHERE username = ? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
    if row is None:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(row["salt"]), PBKDF2_ROUNDS
    ).hex()
    return hmac.compare_digest(candidate, row["password_hash"])


def record_history(
    username: str,
    entry_type: str,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    crop: str | None = None,
    outcome: str | None = None,
    score: float | None = None,
    details: dict | None = None,
) -> None:
    with _connect() as db:
        db.execute(
            """INSERT INTO history
               (username, created_at, entry_type, latitude, longitude, crop, outcome, score, details_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                username,
                _now(),
                entry_type,
                latitude,
                longitude,
                crop,
                outcome,
                score,
                json.dumps(details or {}, ensure_ascii=False),
            ),
        )


def get_history(username: str, limit: int = 50) -> list[dict]:
    with _connect() as db:
        rows = db.execute(
            """SELECT created_at, entry_type, latitude, longitude, crop, outcome, score, details_json
               FROM history WHERE username = ? COLLATE NOCASE
               ORDER BY id DESC LIMIT ?""",
            (username, max(1, min(int(limit), 200))),
        ).fetchall()
    entries = []
    for row in rows:
        entry = dict(row)
        entry["details"] = json.loads(entry.pop("details_json") or "{}")
        entries.append(entry)
    return entries


def cache_key(latitude: float, longitude: float) -> str:
    return f"{float(latitude):.5f},{float(longitude):.5f}"


def get_location_cache(latitude: float, longitude: float) -> dict | None:
    with _connect() as db:
        row = db.execute(
            "SELECT data_json FROM location_cache WHERE cache_key = ?",
            (cache_key(latitude, longitude),),
        ).fetchone()
    return json.loads(row["data_json"]) if row else None


def put_location_cache(latitude: float, longitude: float, data: dict) -> None:
    with _connect() as db:
        db.execute(
            """INSERT INTO location_cache(cache_key, created_at, data_json) VALUES (?, ?, ?)
               ON CONFLICT(cache_key) DO UPDATE SET created_at = excluded.created_at,
                 data_json = excluded.data_json""",
            (cache_key(latitude, longitude), _now(), json.dumps(data, ensure_ascii=False)),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
