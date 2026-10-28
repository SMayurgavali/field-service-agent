import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "field_service.db"


def init_db():
    """Create the complaint history table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS complaint_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                complaint TEXT NOT NULL,
                recommended_part TEXT,
                availability TEXT,
                part_id TEXT,
                stock_quantity TEXT,
                warehouse_location TEXT,
                diagnosis_report TEXT,
                inventory_report TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_complaint(
    complaint,
    diagnosis,
    inventory,
    recommended_part,
    availability,
    part_id,
    stock_quantity,
    warehouse_location,
):
    """Save a completed field-service analysis."""
    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.execute("""
            INSERT INTO complaint_history (
                created_at,
                complaint,
                recommended_part,
                availability,
                part_id,
                stock_quantity,
                warehouse_location,
                diagnosis_report,
                inventory_report
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().astimezone().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            complaint,
            recommended_part,
            availability,
            part_id,
            stock_quantity,
            warehouse_location,
            diagnosis,
            inventory,
        ))

        conn.commit()
        return cursor.lastrowid

    finally:
        conn.close()


def get_recent_complaints(limit=50):
    """Retrieve the latest saved complaint records."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT *
            FROM complaint_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()