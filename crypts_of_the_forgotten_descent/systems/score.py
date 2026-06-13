"""Score calculation and SQLite leaderboard."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from config import (
    SCORE_PER_FLOOR, SCORE_PER_KILL, SCORE_PER_GOLD,
    SCORE_PER_SHARD, SCORE_VICTORY_BONUS,
)

DB_PATH = Path(__file__).parent.parent / "data" / "scores.db"


# ---------------------------------------------------------------------------
# Score formula
# ---------------------------------------------------------------------------

def calculate_score(stats: dict, victory: bool = False) -> int:
    score = (
        stats.get("floors_reached", 0)  * SCORE_PER_FLOOR
        + stats.get("enemies_killed", 0) * SCORE_PER_KILL
        + stats.get("gold_collected", 0) * SCORE_PER_GOLD
        + stats.get("shards_found",   0) * SCORE_PER_SHARD
        + stats.get("turns_survived", 0)
    )
    if victory:
        score += SCORE_VICTORY_BONUS
    return score


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT    NOT NULL,
            score   INTEGER NOT NULL,
            class   TEXT    NOT NULL,
            floors  INTEGER NOT NULL,
            date    TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_score(
    name:  str,
    score: int,
    character_class: str,
    floors: int,
) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO scores (name, score, class, floors, date) VALUES (?,?,?,?,?)",
        (name, score, character_class, floors, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def get_top_scores(limit: int = 10) -> list[dict]:
    conn   = _connect()
    rows   = conn.execute(
        "SELECT name, score, class, floors, date "
        "FROM scores ORDER BY score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "rank":   i + 1,
            "name":   r[0],
            "score":  r[1],
            "class":  r[2],
            "floors": r[3],
            "date":   r[4],
        }
        for i, r in enumerate(rows)
    ]
