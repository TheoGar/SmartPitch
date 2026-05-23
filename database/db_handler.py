import os
import sqlite3
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "/app/data/smartpitch.db")


class DBHandler:
    """Thread-safe SQLite handler for storing player frames and events."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._lock:
            conn = self._get_connection()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS player_frames (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id TEXT NOT NULL,
                        player_id INTEGER NOT NULL,
                        timestamp REAL NOT NULL,
                        x REAL,
                        y REAL,
                        speed REAL,
                        heart_rate INTEGER,
                        fatigue REAL,
                        zone TEXT,
                        cumulative_distance REAL
                    );

                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id TEXT NOT NULL,
                        player_id INTEGER NOT NULL,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_frames_player
                        ON player_frames (match_id, player_id, timestamp);

                    CREATE INDEX IF NOT EXISTS idx_events_player
                        ON events (match_id, player_id, timestamp);
                """)
                conn.commit()
                logger.info("Database initialised at %s", self.db_path)
            finally:
                conn.close()

    def insert_frame(self, frame: dict) -> None:
        sql = """
            INSERT INTO player_frames
                (match_id, player_id, timestamp, x, y, speed, heart_rate, fatigue, zone, cumulative_distance)
            VALUES (:match_id, :player_id, :timestamp, :x, :y, :speed, :heart_rate, :fatigue, :zone, :cumulative_distance)
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(sql, {
                    "match_id": frame.get("match_id", ""),
                    "player_id": frame.get("player_id"),
                    "timestamp": frame.get("timestamp"),
                    "x": frame.get("x"),
                    "y": frame.get("y"),
                    "speed": frame.get("speed"),
                    "heart_rate": frame.get("heart_rate"),
                    "fatigue": frame.get("fatigue"),
                    "zone": frame.get("zone"),
                    "cumulative_distance": frame.get("cumulative_distance"),
                })
                conn.commit()
            except sqlite3.Error as exc:
                logger.error("DB insert_frame error: %s", exc)
            finally:
                conn.close()

    def insert_event(self, match_id: str, player_id: int, timestamp: float, event_type: str) -> None:
        sql = """
            INSERT INTO events (match_id, player_id, timestamp, event_type)
            VALUES (?, ?, ?, ?)
        """
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(sql, (match_id, player_id, timestamp, event_type))
                conn.commit()
            except sqlite3.Error as exc:
                logger.error("DB insert_event error: %s", exc)
            finally:
                conn.close()

    def get_recent_frames(self, match_id: str, player_id: Optional[int] = None, limit: int = 100) -> list[dict]:
        if player_id is not None:
            sql = "SELECT * FROM player_frames WHERE match_id=? AND player_id=? ORDER BY timestamp DESC LIMIT ?"
            params = (match_id, player_id, limit)
        else:
            sql = "SELECT * FROM player_frames WHERE match_id=? ORDER BY timestamp DESC LIMIT ?"
            params = (match_id, limit)
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute(sql, params).fetchall()
                return [dict(row) for row in rows]
            except sqlite3.Error as exc:
                logger.error("DB get_recent_frames error: %s", exc)
                return []
            finally:
                conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import time
    db = DBHandler(db_path="/tmp/test_smartpitch.db")
    frame = {"match_id": "match_001", "player_id": 7, "timestamp": time.time(),
             "x": 42.3, "y": 31.7, "speed": 5.2, "heart_rate": 152,
             "fatigue": 0.74, "zone": "milieu", "cumulative_distance": 150.0}
    db.insert_frame(frame)
    db.insert_event("match_001", 7, time.time(), "sprint")
    rows = db.get_recent_frames("match_001", player_id=7)
    logger.info("Rows retrieved: %d", len(rows))
