import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


class FlightLogRepository:
    """
    SQLite-backed repository for persisting flight logs.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        db_dir = base_dir / "DataBase"
        db_dir.mkdir(parents=True, exist_ok=True)

        self._db_path = Path(db_path) if db_path else db_dir / "flightlogs.sqlite3"
        self._initialize_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _initialize_schema(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS flight_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_uuid TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    stage TEXT,
                    state_key TEXT,
                    map_name TEXT,
                    campaign_name TEXT,
                    mission_status TEXT,
                    player_count INTEGER,
                    log TEXT NOT NULL,
                    metadata TEXT
                );
                """
            )

    def insert_flightlog(
        self,
        logs: Iterable[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, str]:
        """
        Persist a flight log entry.

        Args:
            logs: Iterable of log lines.
            metadata: Optional metadata.

        Returns:
            (row_id, session_uuid)
        """
        lines: List[str] = list(logs)
        if not lines:
            raise ValueError("Cannot insert empty flight log.")

        metadata = dict(metadata or {})
        session_uuid: str = str(metadata.pop("session_uuid", uuid.uuid4()))
        created_at: str = metadata.pop(
            "created_at",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        known_fields = {
            "stage": metadata.pop("stage", None),
            "state_key": metadata.pop("state_key", None),
            "map_name": metadata.pop("map_name", None),
            "campaign_name": metadata.pop("campaign_name", None),
            "mission_status": metadata.pop("mission_status", None),
            "player_count": metadata.pop("player_count", None),
        }

        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        log_payload = json.dumps(lines, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO flight_logs (
                    session_uuid,
                    created_at,
                    stage,
                    state_key,
                    map_name,
                    campaign_name,
                    mission_status,
                    player_count,
                    log,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    session_uuid,
                    created_at,
                    known_fields["stage"],
                    known_fields["state_key"],
                    known_fields["map_name"],
                    known_fields["campaign_name"],
                    known_fields["mission_status"],
                    known_fields["player_count"],
                    log_payload,
                    metadata_json,
                ),
            )
            row_id = cursor.lastrowid

        return row_id, session_uuid


# Module-level singleton for convenience
flightlog_repository = FlightLogRepository()


