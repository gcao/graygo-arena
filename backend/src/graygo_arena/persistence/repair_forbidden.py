"""Repair active games' restrictions from resolved public history, offline.

Boards, moves, captures and transcripts are never replayed or rewritten. A
backend-private backup is required before applying updates to an existing DB.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from graygo_arena.engine import (
    Board,
    ForbiddenState,
    RoundHistory,
    forbidden_after_round,
    legal_moves,
    parse_move,
)


def repair(
    database: Path, *, apply: bool = False, backup: Path | None = None
) -> dict[str, int | bool]:
    if apply and backup is None:
        raise ValueError("a private backup path is required when applying the repair")
    connection = sqlite3.connect(
        database.resolve().as_uri() + ("?mode=rw" if apply else "?mode=ro"), uri=True
    )
    connection.row_factory = sqlite3.Row
    changes: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    try:
        connection.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
        games = connection.execute(
            "SELECT * FROM games WHERE status IN ('created','running','paused')"
        ).fetchall()
        for game in games:
            turns = connection.execute(
                "SELECT * FROM turns WHERE game_id=? ORDER BY turn_index", (game["id"],)
            ).fetchall()
            if turns and turns[-1]["post_board_key"] != game["board_key"]:
                raise ValueError("current game board differs from its resolved history")
            restriction = ForbiddenState()
            history: tuple[RoundHistory, ...] = ()
            for turn in turns:
                before, after = (
                    Board.from_key(turn["pre_board_key"]),
                    Board.from_key(turn["post_board_key"]),
                )
                restriction = forbidden_after_round(
                    before,
                    after,
                    restriction,
                    parse_move(turn["black_move"], before.size),
                    parse_move(turn["white_move"], before.size),
                    history,
                )
                history = (
                    *history,
                    RoundHistory(turn["pre_board_key"], turn["black_move"], turn["white_move"]),
                )[-2:]
            black = sorted(point.to_label() for point in restriction.black)
            white = sorted(point.to_label() for point in restriction.white)
            if black != sorted(json.loads(game["forbidden_black_json"])) or white != sorted(
                json.loads(game["forbidden_white_json"])
            ):
                changes.append(
                    {
                        "game_id": game["id"],
                        "old_black": game["forbidden_black_json"],
                        "old_white": game["forbidden_white_json"],
                        "new_black": black,
                        "new_white": white,
                    }
                )
            board = Board.from_key(game["board_key"])
            for pending in connection.execute(
                "SELECT * FROM pending_moves WHERE game_id=? AND turn_index=?",
                (game["id"], game["current_turn"]),
            ).fetchall():
                color = pending["color"]
                if color not in ("black", "white"):
                    raise ValueError("invalid pending seat color")
                if parse_move(pending["move"], board.size) not in legal_moves(
                    board, color, restriction
                ):
                    removed.append(dict(pending))
        if apply:
            assert backup is not None
            backup.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(
                    {
                        "version": "graygo/restriction-repair/1",
                        "games": changes,
                        "invalid_pending": removed,
                    },
                    stream,
                    indent=2,
                )
                stream.flush()
                os.fsync(stream.fileno())
            for change in changes:
                connection.execute(
                    "UPDATE games SET forbidden_black_json=?,forbidden_white_json=? WHERE id=?",
                    (
                        json.dumps(change["new_black"]),
                        json.dumps(change["new_white"]),
                        change["game_id"],
                    ),
                )
            for pending in removed:
                connection.execute("DELETE FROM pending_moves WHERE id=?", (pending["id"],))
            connection.commit()
        return {
            "games_checked": len(games),
            "games_updated": len(changes),
            "invalid_pending_cleared": len(removed),
            "applied": apply,
        }
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(repair(args.database, apply=args.apply, backup=args.backup)))


if __name__ == "__main__":
    main()
