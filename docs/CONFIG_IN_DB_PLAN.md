# Configuration in the database - plan

Status: implemented and checked against `z21_test`, not yet committed. The analytics migration that
put the events in Postgres is done (`0b87e44` on `develop`, pushed and pulled on the PC).

## Why

The configuration used to be per host, in a tracked `config.json` that the web UI rewrote at
runtime: gates, consists, locomotives, functions, thresholds. So the two machines drifted, every
switch between them needed a manual copy, and a deploy (`git reset --hard`) could destroy the
owner's edits. The database is already one, on the pi4, so the state belongs there too.

## State when this was written

| | |
|---|---|
| writer | none; the PC backend was stopped on purpose, the Mac's is off |
| database | `z21` on the pi4, 105 sessions, 7582 events, CV 71/78 for loco 7 |
| branches | `develop` = `0b87e44` (pushed); `main` = `7ba427b`, behind on purpose (see the end) |
| env | `backend/.env` on both hosts, gitignored, `DATABASE_URL` + `DATABASE_URL_TEST` |
| scratch | `z21_test` on the pi4, disposable |

## What lives where: two layers

1. **Postgres holds one complete config document** (table `config`, a single JSONB row). It is the
   truth. It is seeded from `config.seed.json` only when the row does not exist.
2. **`config.local.json`** keeps machine values and secrets: camera username and password,
   `debug.enabled`. It never enters the database.

Reading is `deep_merge(db_document, local_document)`, with the local one winning.

**Why not three layers** (defaults from the file, merged under the database overrides): a read that
merges the seed back in resurrects deletions. Delete a consist, reload, and `deep_merge` brings it
back from `config.seed.json`. One complete document has no such problem, and there is only one place to
look when a value is wrong.

## Where the database is

The config row lives in whichever database `DATABASE_URL` names: the pi4, the instance started by
`deploy/docker-compose.yml` on the same machine, or one the user already runs. The config code knows
no host and no path, so the three install paths are the same code. On the Docker profile the row
lives in the `z21-pgdata` volume, so `docker compose down -v` deletes the settings together with the
database: that command is a deliberate wipe, and it gets no guard.

## Save path

The shape does not change: every writer does load, mutate, `save_config(whole document)`, and all
five call sites in `routers/config.py` already work this way. What changes is the destination:
`save_config()` writes the database row and replaces the in-memory cache in the same call.
`config.seed.json` is never written at runtime.

The filter stays: camera credentials and `debug.enabled` are removed before the row is written,
because they belong to `config.local.json`.

The writer lock guards sessions, not the config row: if two backends ever run, the last save wins.
That is not new protection to build, it is the same rule as one backend at a time.

**Rejected: write-through to `config.seed.json`.** It would keep the file fresh, but it would also make a
tracked file dirty on every save from the UI, so every `git pull` risks a conflict and every deploy
discards it. The trap it was meant to avoid (an old file wiping months of edits) is closed by the
guard below instead.

## Startup, cache and degradation

- The first read happens at **import**: `video_feed.py:106` runs `load_camera_config()`, which calls
  `load_config()`, and `main.py:22` imports that module before `lifespan` (line 192) calls
  `init_schema()`. At that moment the `config` table may not exist, so the read falls back to the
  file without complaining; the row is read into the cache right after `init_schema()`.
- A fresh process (a script) gets the database on its first `load_config()`: one attempt, and the
  file only if that fails. Without this, a script would read `config.seed.json` and write it back over
  every UI edit, which is the trap this design exists to close.
- `warm_config_cache()` seeds the row when the table is empty, then caches the merged document. It is
  the one call `main.py` makes after `init_schema()`.
- `load_config()` serves an in-memory cache. It is filled from the database at startup and replaced
  on every save; it is called in 51 places, some of them per frame, so a query per call is not an
  option.
- If the database is unreachable at startup, `load_config()` falls back to `config.seed.json`: the app
  starts, the train runs, and the settings UI says that saving is unavailable. A save with the
  database down is an explicit error, never a silent success.
- `reload_config()` re-reads the row into the cache. `POST /api/reload-roster` calls it first, so a
  write made by a script is visible to a running backend without a restart.

## The seed is not a second truth

`scripts/db/load_config.py` loads `config.seed.json` into the database. Once the row exists the
command **refuses** and needs `--force`. A timestamp comparison was rejected: it would compare the
file's mtime on the host with the row's timestamp on the server, two clocks, and would wobble by
seconds. The file is a bootstrap, not a second truth; `--force` is how you say "the file wins".

The name carries the rule: `config.json` invited the reader to treat it as the configuration, which
is why it was renamed. `config.local.json` keeps its name because that one really is a live file.

## Credentials

- `save_config()` keeps stripping camera username and password, and forces `debug.enabled = false`,
  before writing the row.
- `GET /api/config` returns the camera **username** and an **empty password**. A placeholder would be
  posted back on the first save and become the real password, because `SettingsModal.jsx:529` puts
  that value in the input and saves the whole document. The rule instead: an empty incoming password
  keeps the stored one.
- `POST /api/settings/update` must persist local values through `save_local_config()`, not a shallow
  update of the file.
- A failed save must be visible. Today the handler catches the exception and answers HTTP 200 with
  `status: "error"` (`routers/config.py:412`), and `SettingsModal.jsx:112` checks only `response.ok`,
  so it alerts "Settings saved successfully!" and reloads. Return 503 and show the server's message.

## Scripts that touch `config.seed.json` directly

`import_single_locomotive.py`, `import_loco_images.py` and `export_tensorrt.py` read or write the
file; route them through `config_loader`. `save_gates()` copies `config.seed.json` to
`config.seed.json.backup`: with the database as the truth that copy is meaningless, drop it.

**Adding a locomotive is a script, not a config edit.** `scripts/utils/import_single_locomotive.py`
reads the JMRI roster and writes `config["locomotives"]`; after the change it writes the database
through `save_config()`, then `POST /api/reload-roster` refreshes the cache and the locomotive
appears, with no file to edit and no restart. That is the path to document in place of
"edit config.seed.json".

## Steps

1. Table in `init_schema()`; `warm_config_cache()` after it (seed, cache); `load_config()` that
   reads the database on first use in a fresh process and falls back to the file; `save_config()`
   writing the row and the cache; `reload_config()`. Signatures unchanged.
2. Route the direct readers and writers through `config_loader`, call `reload_config()` from
   `POST /api/reload-roster`, remove the file backup.
3. Settings: `GET /api/config` with an empty password and empty-means-keep; `settings/update` through
   `save_local_config()`; a failed save returns 503 and the modal shows the server's message.
4. `scripts/db/load_config.py`, refusing while the row exists unless `--force`.
5. Docs: a config section in `DATABASE_POSTGRES.md`, `AGENTS.md` "Config Files Behavior", the
   locomotive path in the README/deployment skill, `DATABASE_SCHEMA.md`, CHANGELOG.

## Checks run against `z21_test` (2026-11-26)

- Import `video_feed` with the database unreachable and with the table missing: the file answers,
  no traceback.
- Fresh database: `init_schema()` then `warm_config_cache()` seeds from `config.seed.json`.
- A gate moved and saved is visible to a **separate process**, which is the script case, and
  `config.seed.json` mtime does not move.
- A deletion survives a restart (consist 10 stayed deleted).
- `save_config()` with a dead connection raises; over HTTP `POST /api/settings/update` answers 503
  with the reason.
- `GET /api/config` returns an empty camera password; `save-gates` writes nothing to
  `config.seed.json.backup`.

## Acceptance

- Move a gate with the UI on the PC, restart the backend, and the Mac sees the new coordinates with
  no file copy.
- Delete a consist, restart, and it stays deleted.
- With Postgres stopped: the backend starts, the train runs, and the modal reports that saving failed
  instead of claiming success.
- `GET /api/config` contains no camera password, and saving without touching the field keeps the
  stored one.
- `load_config.py` refuses while the row exists; `--force` replaces.
- Import a locomotive with the script while the backend runs, call reload roster, and the locomotive
  appears without a restart.
- After a day of UI edits, `config.seed.json` is byte-identical to the commit: its mtime has not moved.

## Deliberately out of scope

- **`main` stays on the old release until this work lands**, then it is fast-forwarded once. The
  owner chose this; the cost is that `main` still ships the SQLite code until then, and nobody but
  him deploys it.
- No live reload across processes beyond `reload_config()`: one backend at a time, and the cache is
  per process.
- The frontend changes stop at the password contract and the save error, both in `SettingsModal.jsx`:
  no design work, no new settings screen.

## Open question

Advisor recommended fast-forwarding `main` **before** this work, so that a release baseline exists
that speaks Postgres. Declined for now, deliberately: the migration is half done and `main` is not
deployed anywhere.
