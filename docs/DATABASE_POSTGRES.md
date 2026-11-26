# The database

One Postgres database, on the always-on host, read and written by whichever machine runs the backend.
No per-host copy, no manual sync.

## Where it lives

| | |
|---|---|
| host | `pi4`, Debian 12, `100.124.43.88` on Tailscale |
| engine | PostgreSQL 17, from `apt.postgresql.org`, `bookworm-pgdg` |
| database | `z21` (production). `z21_test` is not kept: create it when a check needs a scratch database |
| role | `z21`, `scram-sha-256` |
| access | `pg_hba.conf` allows only `100.64.0.0/10` and localhost; the port is closed everywhere else |
| data | `/var/lib/postgresql/17/main`, on the SD card |

`listen_addresses = '*'` on purpose: binding the Tailscale address directly would keep Postgres from
starting after a reboot whenever `tailscaled` is not up yet.

## Connecting

`backend/.env`, gitignored. The backend reads `DATABASE_URL` only; `DATABASE_URL_TEST` is used by
the scripts in `scripts/db/` and by manual experiments:

```
DATABASE_URL=postgresql://z21:<password>@100.124.43.88:5432/z21
DATABASE_URL_TEST=postgresql://z21:<password>@100.124.43.88:5432/z21_test
```

`python-dotenv` loads it at import in `backend/services/db.py`; the backend never reads a password from
anywhere else. Each connection is short-lived, with `connect_timeout=2` so an unreachable host fails
fast instead of hanging a request.

## One writer

Only one backend runs at a time. That is enforced, not remembered: the process takes a session-level
`pg_try_advisory_lock` at startup. A second backend logs `Another host holds the writer lock` and serves
reads without creating, closing or deleting sessions. This matters because startup normally closes every
session left with `end_time IS NULL` and discards the ones with no Δt: two writers would destroy each
other's work.

The lock dies with the process, so a crash needs no cleanup.

## Schema

Created and extended by `init_schema()` at startup, under an advisory transaction lock, so two hosts
starting together do not race.

Changes are additive: `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`,
`CREATE INDEX IF NOT EXISTS`. One database serves both `develop` and `main`, so a change that drops or
renames a column cannot ship until both branches have moved past it. There is no migration framework,
and nothing to run by hand.

`data.db`, the old SQLite file, is still on the development machines as a rollback and is ignored by git.

## Configuration

The configuration is one document in the `config` table (a single `jsonb` row), not a file: gates,
consists, locomotives, functions, thresholds. The dashboard writes it there, and every host reads the
same one, so a gate moved on the PC is already moved on the Mac.

Two layers:

| | |
|---|---|
| the stored document | what the dashboard edits; the truth |
| `config.local.json` | per machine: camera credentials and `debug.enabled`, merged on top, never stored |

`config.seed.json` is the **seed**: it fills the table the first time the backend starts against an empty
database, and it is never written at runtime. A hand edit of the file counts only after
`venv/bin/python scripts/db/load_config.py`; the command refuses when a document is already stored,
because an old file would otherwise wipe the edits made since the seed. `--force` replaces it.

The backend keeps the merged document in memory: `load_config()` is called in hot paths, some per
frame, so it cannot query per call. `save_config()` writes the row and refreshes the cache together.
A write made outside the backend (the locomotive import script) is picked up by
`POST /api/reload-roster`, which re-reads the row first.

When the database is unreachable the backend still starts, reads `config.seed.json`, and runs the trains;
only saving fails, loudly, in the settings window.

## Backups

On the pi4, a systemd timer checks every 5 minutes and dumps only when the data has been quiet for 15
minutes, so a snapshot never lands in the middle of a run:

1. `pg_dump -Fc` into `/dev/shm`, a RAM disk, so the SD card is not written;
2. the checksum is compared with the newest kept dump, and the file is copied to
   `/mnt/timecapsule/pg/` only if it differs;
3. five dumps are kept, pruned only after the new one is written and listed.

The trigger is the data, not the clock: while the layout runs, events keep arriving and nothing is
dumped. A session left open by a crash does not block it, because the test is the last write, not the
session state.

Source: `scripts/db/pg-dump-if-changed.sh`, installed as `/usr/local/bin/z21-pg-dump`.

**What a backup is worth.** A dump is periodic, so there is always a window: a disaster loses at most
the last twenty minutes of activity, never the sessions already dumped. The only thing that closes that
window further is continuous WAL archiving, which is what a managed instance sells as point-in-time
recovery; it is deliberately not configured here.

## Restore

```sh
# list what is inside, without touching anything
pg_restore -l /mnt/timecapsule/pg/z21-YYYYMMDD-HHMMSS.dump | head

# into a fresh database, never over the live one
sudo -u postgres createdb z21_restore
sudo -u postgres pg_restore -d z21_restore --no-owner <file>
sudo -u postgres psql -d z21_restore -c "select count(*) from sessions, (select 1) x"
```

The dump carries the identity sequence, so `events.id` continues where it stopped. A restore into the
production database is a cutover, not a routine operation: stop the backend first.

## When the database is not there

Tracking continues without it. The analytics logger keeps events in a buffer of 1000 and retries the
write every 10 seconds, printing `Event flush failed, N events kept`; on recovery they are written.
Analytics endpoints return an error instead of blocking the UI, and train control does not depend on the
database. Verified by stopping Postgres for 27 seconds with the layout running: speed and stop commands
still reached the decoder, and the events of that window were all written afterwards.

## Installing it yourself

**On one machine, the short way.** `deploy/docker-compose.yml` starts Postgres 17 with the role and the
database created from environment variables, on `127.0.0.1` only. Copy `.env.example` to `backend/.env`,
`docker compose up -d`, start the backend. The tables are created at the first start.

**Shared between machines, the way this project runs.** Postgres natively on one always-on host:

```sh
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
  https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list
sudo apt-get update && sudo apt-get install -y postgresql-17

sudo -u postgres psql -c "CREATE ROLE z21 LOGIN PASSWORD '<password>'"
sudo -u postgres psql -c "CREATE DATABASE z21 OWNER z21"
sudo -u postgres psql -c "CREATE DATABASE z21_test OWNER z21"
```

Then set `listen_addresses` and restrict `pg_hba.conf` to the network the backends come from, put the
connection string in `backend/.env`, and start the backend against it.
