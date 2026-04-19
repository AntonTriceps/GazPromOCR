"""
SQLite-хранилище для шкафов, записей и карточек устройств.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "gazprom.db"


def _ensure_db_dir():
    DB_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def _get_connection():
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Создание таблиц, если ещё не существуют."""
    with _get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cabinets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cabinet_entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                cabinet_id      INTEGER NOT NULL,
                row_number      INTEGER NOT NULL,
                document_name   TEXT    NOT NULL DEFAULT '',
                serial_number   TEXT    NOT NULL DEFAULT '',
                pages           TEXT    NOT NULL DEFAULT '',
                certificate     TEXT    NOT NULL DEFAULT '',
                created_at      TEXT    NOT NULL,
                FOREIGN KEY (cabinet_id) REFERENCES cabinets(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS device_cards (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id        INTEGER,
                name            TEXT    NOT NULL DEFAULT '',
                serial_number   TEXT    NOT NULL DEFAULT '',
                decimal_number  TEXT    NOT NULL DEFAULT '',
                production_date TEXT    NOT NULL DEFAULT '',
                warranty_period TEXT    NOT NULL DEFAULT '',
                raw_json        TEXT    NOT NULL DEFAULT '{}',
                created_at      TEXT    NOT NULL,
                FOREIGN KEY (entry_id) REFERENCES cabinet_entries(id) ON DELETE SET NULL
            );
        """)


# ---------------------------------------------------------------------------
#  Cabinets
# ---------------------------------------------------------------------------

def create_cabinet(name: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO cabinets (name, created_at) VALUES (?, ?)",
            (name.strip(), now),
        )
        return {
            "id": cursor.lastrowid,
            "name": name.strip(),
            "created_at": now,
        }


def list_cabinets() -> list[dict[str, Any]]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at FROM cabinets ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for row in rows:
            entry_count = conn.execute(
                "SELECT COUNT(*) FROM cabinet_entries WHERE cabinet_id = ?",
                (row["id"],),
            ).fetchone()[0]
            result.append({
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "entry_count": entry_count,
            })
        return result


def delete_cabinet(cabinet_id: int) -> bool:
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM cabinets WHERE id = ?", (cabinet_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
#  Cabinet entries
# ---------------------------------------------------------------------------

def add_entry(
    cabinet_id: int,
    document_name: str,
    serial_number: str = "",
    pages: str = "",
    certificate: str = "",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        # Определяем следующий row_number
        max_row = conn.execute(
            "SELECT COALESCE(MAX(row_number), 0) FROM cabinet_entries WHERE cabinet_id = ?",
            (cabinet_id,),
        ).fetchone()[0]
        row_number = max_row + 1

        cursor = conn.execute(
            """INSERT INTO cabinet_entries
               (cabinet_id, row_number, document_name, serial_number, pages, certificate, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cabinet_id, row_number, document_name, serial_number, pages, certificate, now),
        )
        return {
            "id": cursor.lastrowid,
            "cabinet_id": cabinet_id,
            "row_number": row_number,
            "document_name": document_name,
            "serial_number": serial_number,
            "pages": pages,
            "certificate": certificate,
            "created_at": now,
        }


def list_entries(cabinet_id: int) -> list[dict[str, Any]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """SELECT id, cabinet_id, row_number, document_name, serial_number,
                      pages, certificate, created_at
               FROM cabinet_entries
               WHERE cabinet_id = ?
               ORDER BY row_number""",
            (cabinet_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def delete_entry(entry_id: int) -> bool:
    with _get_connection() as conn:
        cursor = conn.execute("DELETE FROM cabinet_entries WHERE id = ?", (entry_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
#  Device cards
# ---------------------------------------------------------------------------

def save_device_card(
    name: str,
    serial_number: str = "",
    decimal_number: str = "",
    production_date: str = "",
    warranty_period: str = "",
    raw_json: dict | None = None,
    entry_id: int | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    raw = json.dumps(raw_json or {}, ensure_ascii=False)
    with _get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO device_cards
               (entry_id, name, serial_number, decimal_number,
                production_date, warranty_period, raw_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, name, serial_number, decimal_number,
             production_date, warranty_period, raw, now),
        )
        return {
            "id": cursor.lastrowid,
            "entry_id": entry_id,
            "name": name,
            "serial_number": serial_number,
            "decimal_number": decimal_number,
            "production_date": production_date,
            "warranty_period": warranty_period,
            "raw_json": raw_json or {},
            "created_at": now,
        }


def get_device_card(card_id: int) -> dict[str, Any] | None:
    with _get_connection() as conn:
        row = conn.execute(
            """SELECT id, entry_id, name, serial_number, decimal_number,
                      production_date, warranty_period, raw_json, created_at
               FROM device_cards WHERE id = ?""",
            (card_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["raw_json"] = json.loads(result["raw_json"])
        return result


def list_device_cards() -> list[dict[str, Any]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """SELECT id, entry_id, name, serial_number, decimal_number,
                      production_date, warranty_period, created_at
               FROM device_cards ORDER BY created_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]


# Инициализация при импорте
init_db()
