"""Small SQLite database wrapper."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any


class SQLiteDatabase:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._configure()
        self._create_schema()

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> None:
        with self._lock, self._connection:
            self._connection.execute(sql, parameters)

    def fetch_one(self, sql: str, parameters: tuple[object, ...] = ()) -> sqlite3.Row:
        with self._lock:
            row = self._connection.execute(sql, parameters).fetchone()
        if row is None:
            msg = "row not found"
            raise KeyError(msg)
        return row

    def fetch_all(self, sql: str, parameters: tuple[object, ...] = ()) -> tuple[sqlite3.Row, ...]:
        with self._lock:
            rows = self._connection.execute(sql, parameters).fetchall()
        return tuple(rows)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _configure(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA busy_timeout = 5000")

    def _create_schema(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS games (
              id TEXT PRIMARY KEY,
              board_size INTEGER NOT NULL,
              ruleset TEXT NOT NULL,
              status TEXT NOT NULL,
              current_turn INTEGER NOT NULL,
              board_key TEXT NOT NULL,
              forbidden_black_json TEXT NOT NULL,
              forbidden_white_json TEXT NOT NULL,
              double_pass_count INTEGER NOT NULL,
              black_seat_id TEXT NOT NULL,
              white_seat_id TEXT NOT NULL,
              max_turns INTEGER NOT NULL,
              invalid_move_policy TEXT NOT NULL,
              show_private_summaries_in_ui INTEGER NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS seat_sessions (
              id TEXT PRIMARY KEY,
              game_id TEXT NOT NULL,
              color TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              credential_ref TEXT NOT NULL,
              local_history_json TEXT NOT NULL,
              provider_session_id TEXT,
              previous_response_id TEXT,
              script_json TEXT NOT NULL,
              FOREIGN KEY (game_id) REFERENCES games(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS turns (
              id TEXT PRIMARY KEY,
              game_id TEXT NOT NULL,
              turn_index INTEGER NOT NULL,
              pre_board_key TEXT NOT NULL,
              post_board_key TEXT NOT NULL,
              black_move TEXT NOT NULL,
              white_move TEXT NOT NULL,
              status TEXT NOT NULL,
              resolution_json TEXT NOT NULL,
              FOREIGN KEY (game_id) REFERENCES games(id),
              UNIQUE (game_id, turn_index)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS pending_moves (
              id TEXT PRIMARY KEY,
              game_id TEXT NOT NULL,
              turn_index INTEGER NOT NULL,
              seat_session_id TEXT NOT NULL,
              color TEXT NOT NULL,
              move TEXT NOT NULL,
              source TEXT NOT NULL,
              raw_response TEXT NOT NULL,
              valid INTEGER NOT NULL,
              error TEXT,
              attempt INTEGER NOT NULL,
              FOREIGN KEY (game_id) REFERENCES games(id),
              FOREIGN KEY (seat_session_id) REFERENCES seat_sessions(id),
              UNIQUE (game_id, turn_index, color)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_calls (
              id TEXT PRIMARY KEY,
              game_id TEXT NOT NULL,
              turn_index INTEGER NOT NULL,
              seat_session_id TEXT NOT NULL,
              color TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              prompt_board_key TEXT NOT NULL,
              raw_response TEXT NOT NULL,
              parsed_move TEXT NOT NULL,
              valid INTEGER NOT NULL,
              error TEXT,
              attempt INTEGER NOT NULL,
              FOREIGN KEY (game_id) REFERENCES games(id),
              FOREIGN KEY (seat_session_id) REFERENCES seat_sessions(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS seat_transcripts (
              id TEXT PRIMARY KEY,
              game_id TEXT NOT NULL,
              turn_index INTEGER NOT NULL,
              seat_session_id TEXT,
              view TEXT NOT NULL,
              text TEXT NOT NULL,
              FOREIGN KEY (game_id) REFERENCES games(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS events (
              id TEXT PRIMARY KEY,
              game_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              FOREIGN KEY (game_id) REFERENCES games(id)
            )
            """,
        )
        with self._lock, self._connection:
            for statement in statements:
                self._connection.execute(statement)


def row_value(row: sqlite3.Row, key: str) -> Any:
    return row[key]
