Historical, kept as a record. Not current.

# Postgres migration - plan

Status: drafted, reviewed by advisor, not implemented. Supersedes the plan
sketched before the pi4 upgrade; the sections marked "changed" are what that
upgrade settled.

## Goal

One copy of the analytics database, on the pi4, reachable by whichever host runs
the backend.

The cost it removes is daily. Development happens on the Mac, which captures
video better than the PC; away from home the PC keeps the backend running and the
Mac connects to it. Every switch today means copying `data.db` by hand or
accepting that the two files drift apart, and a session recorded on one host is
invisible on the other until someone copies it. The drift is not hypothetical:
the last merge of the two files had to reconcile three sessions and 207 events.

Secondary, and the reason the shape matters: z21-Terminal is the owner's private
working copy of the stack his employer sells, where the database lives in the
cloud. One authoritative database, one writer, backups with a tested restore and
additive schema changes are the parts worth practising. An AWS managed instance
is replaced here by an always-on machine on Tailscale; that difference is the
accepted trade, not an oversight.

Non-goals: rewriting the z21-OpenSearch demo, which keeps its snapshot and its
HTTP contract; UI work; WordPress; multi-tenant; high availability.

## Host: pi4

| | |
|---|---|
| OS | Debian 12.15, kernel 6.12.115 (upgraded 2026-11-25) |
| Resources | 4 cores, 3.7 GB RAM (331 MB used), 37 GB free on `/`, 489 GB free on `/mnt/timecapsule` |
| Address | Tailscale `100.124.43.88`, node `pi4` |
| Postgres | **17 from apt.postgresql.org, bookworm suite** (verified available; the bullseye suite no longer exists there) |

**Changed:** PG17 installs natively. No Docker and no container on the host, so
option A of the earlier draft is dead and the "PG13 from Debian" fallback is
moot. Debian's own bullseye was the only reason those existed.

**Changed:** the test instance is a second database (`z21_test`) on the same
server, not a Postgres container on the Mac (Docker is not installed there).
Same engine, same network path as production, nothing extra to maintain.

Configuration: `listen_addresses = '*'` with `pg_hba.conf` restricted to
`100.64.0.0/10` and localhost, `scram-sha-256`, dedicated role and database
(`z21`). Binding to the Tailscale address itself is rejected: `postgresql.service`
would then fail at boot whenever `tailscaled` has not come up yet, and the
`pg_hba.conf` restriction already gives the same exposure. Connection string in
`backend/.env` on each host (gitignored), loaded with `python-dotenv`, which is
already a dependency but is never loaded today.

WAL on the SD card is acceptable at this write volume: a session is a few
hundred KB. Worth a line in the doc, not a redesign.

**Backups.** Everything runs on the pi4, which is always on; the backend on the Mac
or the PC knows nothing about it. A systemd timer runs every 5 minutes, and the
dump happens when the data is quiet, meaning no write for 15 minutes: neither the
clock nor the boot decides the snapshot, the data does. While the railway runs,
events keep arriving and the condition is false, so it never fires while something
is being written, and it fires on its own about 20 minutes after the train stops,
before the 30-minute idle timeout closes the session (`tracking_daemon.py:364-395`).
A pause longer than 15 minutes can produce a snapshot while the session is still
open, which is harmless: nothing is changing.

The script dumps with `pg_dump -Fc` into `/dev/shm` (a RAM disk, so the SD card is
not touched), compares the checksum with the newest kept dump, copies to
`/mnt/timecapsule/pg/` only if different, and keeps **five** files. Five covers the
last five times the layout was used, two levels of fallback behind the newest, and
costs 500 MB in the worst case of a 100 MB dump on a 500 GB disk. Pruning happens
only after the new dump is written and verified, and the oldest file is deleted only
when a newer valid one exists, so the history never reaches zero.

A fingerprint of the tables was rejected as the "did it change" test: it has to
guess which column moves on an in-place update, and it misses a delete. At two
megabytes a dump, dumping first and comparing after is simpler and cannot lie.
The quiet rule also survives a dead backend: the "last write" test does not look at
session state, so a session left with `end_time IS NULL` by a crash cannot block the
backup for ever.

One case the timer cannot cover is the one where "before" matters: a schema change
or a cutover. Those get an explicit `pg-dump` first, as part of the deploy, because
a copy taken after a bad migration is worthless.

**Loss window.** A dump is periodic, so no scheme of dumps removes the gap. With
these numbers, a disaster loses at most the last ~20 minutes of activity, which in
practice is the session just recorded, and never the sessions already dumped. The
only thing that closes the gap further is continuous WAL archiving, which is what a
managed instance calls point-in-time recovery; it is a second process to keep
working, and the plan leaves it out as the next step if the project ever needs it.

A dump is still a snapshot, not a live copy: restoring means `pg_restore` into a
fresh database, and this plan counts the backup done only after one restore brought
the counts back. The dump and Time Machine share the same USB disk, so losing that
disk loses both; a second copy elsewhere is a few lines in the script and is
deliberately left out of the first pass.

## Code surface

57 statements in four files, no ORM:

| file | statements | Postgres-specific work |
|---|---|---|
| `backend/services/data_db.py` | 34 | 26 `json_extract` -> `(data->>'k')::type`, 4 `ON CONFLICT` (syntax already compatible) |
| `backend/services/speed_table_helpers.py` | 8 | 1 `INSERT OR REPLACE` -> `ON CONFLICT DO UPDATE` |
| `backend/analytics_logger.py` | 7 | 1 `AUTOINCREMENT`, schema creation |
| `backend/routers/*.py` | 8 | `validated = 0/1` stays an integer |
| `backend/tracking_daemon.py` | 2 | direct `sqlite3` calls replaced by a `DataDB` method |

Traps found reading the code, none of them visible from the statement count:

- `MAX(last_active_time, ?)` (`analytics_logger.py:278`) is SQLite scalar syntax;
  Postgres needs `GREATEST(last_active_time, %s)`.
- `executescript()` (`analytics_logger.py:61`) does not exist in psycopg: the
  schema block has to be split into statements.
- `COALESCE(auto_compensation_enabled, 1)` (`data_db.py:988`) fails if that
  column becomes `boolean`; either keep it integer or coalesce to `false`.
- `(data->>'k')` is `text`: every numeric comparison, `ORDER BY` and `AVG()` needs
  an explicit `::int` or `::double precision`.
- `json.loads` appears eleven times, not eight, `routers/speed_table.py:313`
  included; with `JSONB` psycopg returns a dict, so all of them go, and that one
  hides inside a bare `except` that would swallow the `TypeError`.

Decisions:

- **Timestamps stay Unix epoch in `double precision`.** No `timestamptz`: it
  would change every API payload for no gain. `to_timestamp()` is there for
  ad-hoc queries. Only `last_modified` / `last_updated`, never returned by the
  API, become `timestamptz`.
- **`events.data` and `previous_values` become `JSONB`.** psycopg returns
  dicts, so the eleven `json.loads` calls go away. Writes use `%s::jsonb`, so the
  logger's buffer keeps its shape.
- `validated` stays `integer` 0/1: `WHERE validated = 1` needs no change.
- `events.id` is an identity column, and the migration inserts explicit ids then
  advances the sequence with `setval`; the frontend deletes events by id.
- `DataDB.get_connection()` returns a fresh `psycopg.connect()` per call, which
  matches the existing open/close pattern, with `connect_timeout=2` so a dead
  host fails fast instead of stalling the caller. No pool until a measurement
  asks for one.
- `migrate_speed_table_decoder_support()` has one caller, not zero:
  `scripts/migrate_decoder_metadata.py`, whose own docstring says it is a one-shot
  migration from 2026-01-20 that can be deleted after running. Both go. The function
  is the only place holding a `PRAGMA` (`table_info`), which has no Postgres
  equivalent, and the three columns it added are already in the schema.
- Schema changes are additive and applied by `init_schema()`: `CREATE TABLE IF
  NOT EXISTS`, plus an ordered list of `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  and `CREATE INDEX IF NOT EXISTS`, under `pg_advisory_xact_lock` because both
  hosts can start at once. No migration framework: one database serves both
  `develop` and `main`, so a change that drops or renames a column cannot ship
  until both branches have moved past it.

**Single writer, enforced.** The rule that Mac and PC never run at once is not
enough by itself. A second backend starting today closes every session with
`end_time IS NULL` and deletes the ones without `delta_t`
(`analytics_logger.py:106-131`), and the idle rotation deletes unvalidated
sessions (`analytics_logger.py:233`, `tracking_daemon.py:472`). So the writer
takes a session-level `pg_try_advisory_lock` at startup: a host that does not get
it serves reads, logs why, and refuses to write. That is the whole mechanism, no
`host` column and no lease table.

**Risk to measure.** `get_critical_events_by_speed` issues roughly 500 queries
(one round of counts per speed). Over a direct Tailscale path it is fine; over a
relayed tunnel it could take seconds. Measure it against `z21_test` in step 4; if
it exceeds ~2 s, collapse the per-speed loop into one `GROUP BY`.

## Data to migrate

Source: the PC's `backend/data/data.db`, with the PC backend stopped. The Mac
copy was merged into it already (101 sessions and 7,254 events before, 104 and
7,461 after), so the two files now hold the same data and no further merge is due
before the cutover.

- 104 validated sessions plus 1 empty one (`validated = 0`, no events)
- 7,461 events (`yolo_performance` 5,558, `delta_t` 1,389, `speed_setting` 478,
  `loco_operating_time` 36)
- 5 locomotives in `locomotive_stats`, 7 in the speed table, 196 CV timestamps,
  2 consist states, 1 system state

## Steps

The order matters: the test database lives on the pi4, so the host is provisioned
before anything is tested against it.

1. **Host.** pgdg repo, `postgresql-17`, role `z21`, databases `z21` and
   `z21_test`, `listen_addresses` and `pg_hba.conf`, the 5-minute dump timer with
   the 15-minute quiet rule and five kept files, and **one restore drill**. Nothing
   is migrated yet.
2. **Schema.** DDL, `init_schema()`, indexes on `(session_id, event_type)` and
   `(event_type, timestamp)`, foreign keys.
3. **Migration script** `scripts/db/sqlite_to_postgres.py`, run against
   `z21_test`: reads the SQLite file read-only, preserves ids, advances the
   sequence, and asserts
   - the seven table counts,
   - foreign-key integrity,
   - `SUM(delta_t)` per consist against the source,
   - `locomotive_stats` against a recomputation from `loco_operating_time`
     events, using the same rule as `analytics_logger.log_loco_operating_time`
     (the assertions in z21-OpenSearch `tools/merge_databases.py` are the model).
   A failed assertion exits non-zero.
4. **Data layer.** Rewrite the 57 statements in the four files plus the two
   direct `sqlite3` calls; add `psycopg[binary]` to `requirements.txt` and load
   `DATABASE_URL`. No SQLite fallback: two dialects for 26 JSON extractions is
   more than it protects. Then test on the Mac against `z21_test`: analytics
   endpoints, reports, speed table, CV write in dry-run, the latency measurement
   above, and the kill-DB drill (stop Postgres during train control and check the
   WebSocket commands still answer).

   Three fixes belong to this step, because without them the degradation claimed
   under Acceptance is false: `connect_timeout=2` on every connection, the event
   buffer cleared only after a successful commit
   (`analytics_logger.py:181-185` currently clears it first), and
   `except psycopg.OperationalError` around the `DataDB` calls that sit on the
   event loop (`z21_manager.py:703-805`,
   `websocket_handlers/ws_control.py:235`).
5. **Cutover.** PC backend stopped, `data.db` copied aside, migration run,
   `DATABASE_URL` in `.env` on PC and Mac, backend started, endpoint comparison
   and counts re-run. `data.db` stays as the rollback.
6. **Docs.** `docs/DATABASE_POSTGRES.md`, `docs/DATABASE_SCHEMA.md` rewritten in
   Postgres SQL, `AGENTS.md` (where the DB lives, backups, the `.env`), CHANGELOG,
   and the reciprocal pointer to z21-OpenSearch.

## Acceptance

- The existing endpoints return the same data: sessions, events, analytics,
  speed table.
- No loss: 104 validated sessions, 7,461 events, 5 stats rows.
- The original `data.db` is still recoverable.
- A scheduled backup exists and has been restored once, with the counts coming
  back.
- No dump is written while a session is recording, and one appears within about 20
  minutes of the last write; five files are kept, and the newest is a valid archive.
- Starting a second backend while the first is recording leaves the first
  session untouched: the second refuses to write and says so.
- With the database stopped during train control, WebSocket speed and stop
  commands still answer and analytics endpoints return 500. Until the three fixes
  in step 4 exist this bullet is not met, whatever the code claims today.

## Open items

- One database for both `develop` and `main`, so schema changes must be
  additive; both branches must tolerate the current schema.
- The z21 `.gitignore` change (`backend/data/data.db*`, which also covers
  `-wal` and `-shm`) rides with this work.
- `tools/merge_databases.py` in z21-OpenSearch becomes historical after the
  cutover; the demo keeps using a snapshot.
- `scripts/utils/import_single_locomotive.py` reads the JMRI roster and writes
  CV67-94, CV2, CV5 and the decoder type straight into `backend/data/data.db` with
  its own `sqlite3.connect()` (`:161`). After the cutover those writes land in a file
  nobody reads. It has to go through `DataDB` like everything else.
