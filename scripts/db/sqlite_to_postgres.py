#!/usr/bin/env python3
"""
Copy the SQLite analytics database into Postgres.

Reads the SQLite file read-only, keeps every event id (the frontend deletes by
id), and fails loudly if the copy does not match the source. Destructive on the
target: the seven tables are truncated first.

Usage:
    DATABASE_URL=postgresql://... python scripts/db/sqlite_to_postgres.py \\
        --sqlite backend/data/data.db [--recompute-stats-off]
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from services import db  # noqa: E402  (needs backend on the path)

TABLES = [
    "sessions",
    "events",
    "locomotive_stats",
    "locomotive_speed_table",
    "consist_state",
    "system_state",
    "cv_modification_timestamps",
]

CV_COLUMNS = [f"cv{i}" for i in range(67, 95)]


def parse_json(value, where):
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise SystemExit(f"invalid JSON in {where}: {e}")


def sqlite_rows(conn, table):
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]


def insert(conn, table, columns, rows):
    if not rows:
        return
    placeholders = ", ".join(["%s"] * len(columns))
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            rows,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True, help="path to data.db")
    ap.add_argument("--url", default=None, help="target database (default: DATABASE_URL)")
    args = ap.parse_args()

    load_dotenv(PROJECT_ROOT / "backend" / ".env")
    url = args.url or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("no target database: pass --url or set DATABASE_URL")

    src = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)

    os.environ["DATABASE_URL"] = url
    db.init_schema()

    with psycopg.connect(url, autocommit=False) as dst:
        dst.execute("SET TIME ZONE 'UTC'")
        dst.execute(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")

        sessions = sqlite_rows(src, "sessions")
        insert(dst, "sessions", ["id", "start_time", "end_time", "validated", "event_count"],
               [(r["id"], r["start_time"], r["end_time"], int(r["validated"] or 0), r["event_count"] or 0)
                for r in sessions])

        events = sqlite_rows(src, "events")
        insert(dst, "events", ["id", "session_id", "timestamp", "event_type", "data"],
               [(r["id"], r["session_id"], r["timestamp"], r["event_type"],
                 json.dumps(parse_json(r["data"], f"events.id={r['id']}")))
                for r in events])
        dst.execute("SELECT setval(pg_get_serial_sequence('events', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM events), 1), "
                    "(SELECT MAX(id) FROM events) IS NOT NULL)")

        stats = sqlite_rows(src, "locomotive_stats")
        insert(dst, "locomotive_stats",
               ["address", "name", "total_operating_seconds", "total_sessions",
                "last_active_time", "created_at", "updated_at"],
               [tuple(r[c] for c in ["address", "name", "total_operating_seconds", "total_sessions",
                                     "last_active_time", "created_at", "updated_at"])
                for r in stats])

        speed = sqlite_rows(src, "locomotive_speed_table")
        speed_cols = ["loco_address"] + CV_COLUMNS + [
            "previous_values", "last_modified", "source", "vstart", "vhigh", "decoder_type"]
        insert(dst, "locomotive_speed_table", speed_cols,
               [tuple(
                   json.dumps(parse_json(r["previous_values"], f"speed_table address={r['loco_address']}"))
                   if c == "previous_values" else r[c]
                   for c in speed_cols
               ) for r in speed])

        consist = sqlite_rows(src, "consist_state")
        insert(dst, "consist_state", ["consist_id", "virtual_mode", "auto_compensation_enabled", "last_updated"],
               [(r["consist_id"], bool(r["virtual_mode"]), bool(r["auto_compensation_enabled"]), r["last_updated"])
                for r in consist])

        state = sqlite_rows(src, "system_state")
        insert(dst, "system_state", ["key", "value", "last_updated"],
               [(r["key"], r["value"], r["last_updated"]) for r in state])

        cvs = sqlite_rows(src, "cv_modification_timestamps")
        insert(dst, "cv_modification_timestamps", ["loco_address", "step", "cv_last_modified"],
               [(r["loco_address"], r["step"], r["cv_last_modified"]) for r in cvs])

        dst.commit()

        # --- assertions ---------------------------------------------------
        failures = []
        for table in TABLES:
            want = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            got = dst.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if want != got:
                failures.append(f"{table}: source {want}, target {got}")

        orphan = dst.execute(
            "SELECT COUNT(*) FROM events e LEFT JOIN sessions s ON s.id = e.session_id "
            "WHERE s.id IS NULL").fetchone()[0]
        if orphan:
            failures.append(f"events without session: {orphan}")

        # delta_t totals per consist, recomputed from the copied jsonb. Rounded in
        # Python: SQLite returns floats and psycopg returns Decimal for SUM().
        want = {cid: round(float(total or 0), 3) for cid, total in src.execute(
            "SELECT json_extract(data, '$.consist_id'), SUM(json_extract(data, '$.delta_t')) "
            "FROM events WHERE event_type = 'delta_t' GROUP BY 1").fetchall()}
        got = {cid: round(float(total or 0), 3) for cid, total in dst.execute(
            "SELECT (data->>'consist_id')::int, SUM((data->>'delta_t')::double precision) "
            "FROM events WHERE event_type = 'delta_t' GROUP BY 1").fetchall()}
        if want != got:
            failures.append(f"delta_t totals per consist differ: {set(want.items()) ^ set(got.items())}")

        # locomotive_stats must cover at least the operating time its own events prove
        proven = {address: float(seconds or 0) for address, seconds in dst.execute(
            "SELECT (data->>'address')::int, "
            "SUM((data->>'duration_seconds')::double precision) "
            "FROM events WHERE event_type = 'loco_operating_time' GROUP BY 1").fetchall()}
        stored = {address: float(seconds or 0) for address, seconds in dst.execute(
            "SELECT address, total_operating_seconds FROM locomotive_stats").fetchall()}
        for address, seconds in proven.items():
            if stored.get(address, 0) + 1 < seconds:
                failures.append(
                    f"loco {address}: stats say {stored.get(address)} s, events prove {seconds} s")

        print(f"sessions {len(sessions)}, events {len(events)}, speed tables {len(speed)}, "
              f"stats {len(stats)}, cv timestamps {len(cvs)}")
        if failures:
            print("FAILED:")
            for f in failures:
                print("  -", f)
            return 1
        print("all assertions passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
