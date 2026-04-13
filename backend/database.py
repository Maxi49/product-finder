import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "store.db"

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS stores (
                id          TEXT PRIMARY KEY,
                admin_token TEXT NOT NULL,
                name        TEXT NOT NULL,
                whatsapp    TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id          TEXT PRIMARY KEY,
                store_id    TEXT NOT NULL REFERENCES stores(id),
                name        TEXT NOT NULL,
                price       REAL,
                image_hint  TEXT,
                position    INTEGER
            );
        """)

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def generate_store_id() -> str:
    return uuid.uuid4().hex[:8]

def generate_token() -> str:
    return str(uuid.uuid4())
