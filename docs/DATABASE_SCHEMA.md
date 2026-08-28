# Database Schema - data.db

**Location**: `backend/data/data.db`
**Type**: SQLite 3
**Purpose**: Analytics, speed tables, locomotive stats, consist state

---

## Tables Overview

| Table | Purpose | Records (approx) |
|-------|---------|------------------|
| `sessions` | Analytics session tracking | ~hundreds |
| `events` | Time-series analytics events | ~thousands |
| `locomotive_stats` | Operating time per locomotive | 7 (one per loco) |
| `locomotive_speed_table` | CV67-94 speed tables | 7 (one per loco) |
| `cv_modification_timestamps` | Per-CV modification timestamps | 196 (7 locos × 28 steps) |
| `consist_state` | Virtual Mode + Auto Compensation state | 2 (one per consist) |
| `system_state` | System-wide key-value state | ~few |

---

## Table: sessions

**Purpose**: Analytics session tracking (start/end time, event count)

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,              -- Format: YYYYMMDD_HHMMSS
    start_time REAL,                  -- Unix timestamp (float)
    end_time REAL,                    -- Unix timestamp (float)
    validated BOOLEAN DEFAULT 0,      -- Session validation flag
    event_count INTEGER DEFAULT 0     -- Number of events in session
);
```

**Example**:
```
id: "20260112_115038"
start_time: 1768215038.47
end_time: 1768215190.24
validated: 1
event_count: 42
```

---

## Table: events

**Purpose**: Time-series analytics events (Δt, speed settings, YOLO performance, operating time)

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,                  -- FK to sessions.id
    timestamp REAL,                   -- Unix timestamp (float)
    event_type TEXT,                  -- Type: delta_t, speed_setting, loco_operating_time, yolo_performance
    data TEXT,                        -- JSON payload (structure varies by event_type)
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_session_type ON events(session_id, event_type);
CREATE INDEX idx_timestamp ON events(timestamp);
```

### Event Types

#### 1. `delta_t` - Gate crossing timing delta

**Purpose**: Track synchronization between lead/rear locomotives

**JSON structure**:
```json
{
  "consist_id": 11,
  "delta_t": -0.944,
  "status": "SYNCED",          // SYNCED | WARNING | CRITICAL
  "gate_type": "L7G2-L8G1",    // Lead gate - Rear gate
  "speed": 88                  // DCC speed setting (0-126)
}
```

**Status thresholds** (from `config.json`):
- `SYNCED`: |Δt| < 1.0s
- `WARNING`: 1.0s ≤ |Δt| < 1.5s
- `CRITICAL`: |Δt| ≥ 1.5s

**Query examples**:
```sql
-- Find all CRITICAL delta_t events
SELECT * FROM events
WHERE event_type='delta_t'
  AND json_extract(data, '$.status')='CRITICAL';

-- Find outliers (|Δt| > 3s)
SELECT id, timestamp, data FROM events
WHERE event_type='delta_t'
  AND (json_extract(data, '$.delta_t') > 3.0
       OR json_extract(data, '$.delta_t') < -3.0);

-- Average Δt for consist 11
SELECT AVG(json_extract(data, '$.delta_t')) as avg_delta_t
FROM events
WHERE event_type='delta_t'
  AND json_extract(data, '$.consist_id')=11;
```

#### 2. `speed_setting` - DCC speed changes

**Purpose**: Track speed setting changes for locomotives/consists

**JSON structure**:
```json
{
  "address": 11,
  "consist_id": 11,
  "speed_old": 0,
  "speed_new": 88,
  "forward": true,
  "source": "web_ui"          // web_ui | migration_historical | auto_compensation
}
```

#### 3. `loco_operating_time` - Locomotive operating duration

**Purpose**: Track how long each locomotive runs per session

**JSON structure**:
```json
{
  "address": 7,
  "start_time": 1768215038.47,
  "end_time": 1768215190.24,
  "duration_seconds": 151.77,
  "session_id": "20260112_115038",
  "consist_id": 11
}
```

#### 4. `yolo_performance` - YOLO tracking metrics

**Purpose**: Track YOLO detection performance (FPS, confidence, miss rate)

**JSON structure**:
```json
{
  "avg_fps": 2.20,
  "avg_confidence": {
    "8": 0.763,              // Loco 8 average confidence
    "1": 0.656,
    "7": 0.593
  },
  "miss_rate": 1.0           // Percentage of frames with no detections
}
```

---

## Table: locomotive_stats

**Purpose**: Aggregate statistics per locomotive (total operating time, session count)

```sql
CREATE TABLE locomotive_stats (
    address INTEGER PRIMARY KEY,      -- DCC address (1-8)
    name TEXT,                        -- Locomotive name
    total_operating_seconds INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    last_active_time REAL,            -- Unix timestamp
    created_at REAL,
    updated_at REAL
);
```

**Example**:
```
address: 7
name: "E656 239"
total_operating_seconds: 45620
total_sessions: 18
last_active_time: 1768774968.73
```

---

## Table: locomotive_speed_table

**Purpose**: Store CV67-94 speed tables (28 steps) + decoder metadata for each locomotive

```sql
CREATE TABLE locomotive_speed_table (
    loco_address INTEGER PRIMARY KEY,
    cv67 INTEGER NOT NULL CHECK(cv67 BETWEEN 0 AND 255),
    cv68 INTEGER NOT NULL CHECK(cv68 BETWEEN 0 AND 255),
    -- ... cv69-cv93 (same structure)
    cv94 INTEGER NOT NULL CHECK(cv94 BETWEEN 0 AND 255),
    vstart INTEGER,                   -- CV2 (Vstart) for ESU decoders, NULL for NMRA
    vhigh INTEGER,                    -- CV5 (Vhigh) for ESU decoders, NULL for NMRA
    decoder_type TEXT,                -- 'esu_mfx' or 'nmra_standard'
    previous_values TEXT,             -- JSON backup of previous values
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'jmri_import' -- jmri_import | web_ui | auto_adjust | undo
);

CREATE INDEX idx_loco_speed_table_modified
    ON locomotive_speed_table(last_modified DESC);
```

**Example (ESU decoder)**:
```
loco_address: 1
cv67: 1, cv68: 12, cv69: 15, ..., cv94: 255
vstart: 2                           -- CV2 (min speed endpoint)
vhigh: 133                          -- CV5 (max speed endpoint)
decoder_type: "esu_mfx"
previous_values: {"cv67": 1, "cv68": 10, ...}
last_modified: 2026-01-20 14:32:18
source: "web_ui"
```

**Example (NMRA decoder)**:
```
loco_address: 7
cv67: 12, cv68: 15, cv69: 18, ..., cv94: 255
vstart: NULL                        -- NMRA decoders don't use CV2/CV5 as endpoints
vhigh: NULL
decoder_type: "nmra_standard"
previous_values: {"cv67": 10, "cv68": 13, ...}
last_modified: 2026-01-18 23:45:12
source: "web_ui"
```

**Notes**:
- **CV67-94** = 28 speed steps (JMRI standard mapping)
- **Values**: 0-255 (motor PWM duty cycle)
- **ESU mfx decoders** (LokSound, LokPilot):
  - CV67 (step 1) = FIXED at 1 (read-only)
  - CV94 (step 28) = FIXED at 255 (read-only)
  - CV68-93 (steps 2-27) = Scaled between CV2 (Vstart) and CV5 (Vhigh)
  - Edit CV2/CV5 to adjust min/max speed endpoints
- **NMRA standard decoders** (Hornby TXS, Zimo MX630):
  - CV67-94 all editable (0-255)
  - CV2/CV5 not used as speed table endpoints
- **previous_values**: JSON backup for 1-level undo
- **source** values: `jmri_import`, `jmri_reimport`, `web_ui`, `test_mode`, `undo`

---

## Table: cv_modification_timestamps

**Purpose**: Track per-CV modification timestamps for speed table filtering (28 steps per locomotive)

```sql
CREATE TABLE cv_modification_timestamps (
    loco_address INTEGER NOT NULL,
    step INTEGER NOT NULL CHECK(step BETWEEN 1 AND 28),
    cv_last_modified REAL DEFAULT 0,  -- Unix timestamp (0 = never modified)
    PRIMARY KEY (loco_address, step),
    FOREIGN KEY (loco_address) REFERENCES locomotive_speed_table(loco_address)
);

CREATE INDEX idx_cv_timestamps_loco
    ON cv_modification_timestamps(loco_address);
```

**Example**:
```
loco_address: 1
step: 15
cv_last_modified: 1737492738.25  -- Unix timestamp (2026-01-21 23:12:18)
```

**Notes**:
- **28 rows per locomotive** (step 1-28, corresponding to CV67-94)
- **cv_last_modified = 0**: CV never modified (initial state after import)
- **cv_last_modified > 0**: Last time this specific CV was modified via web UI
- **Purpose**: Filter delta_t events by CV modification time
  - When CV76 is modified → ignore events before that timestamp
  - Recommendations disappear immediately after "Apply & Write"
  - Reappear only if new tests (after modification) are still CRITICAL
- **Updated by**: Speed Table Viewer "Apply & Write to Decoder" button
- **Total rows**: 7 locomotives × 28 steps = 196 rows

**Query examples**:
```sql
-- Get all CV timestamps for locomotive 1
SELECT step, cv_last_modified
FROM cv_modification_timestamps
WHERE loco_address = 1
ORDER BY step;

-- Get CV timestamp for specific step (e.g., step 15 → CV81)
SELECT cv_last_modified
FROM cv_modification_timestamps
WHERE loco_address = 1 AND step = 15;

-- Find recently modified CVs (last 24 hours)
SELECT loco_address, step, datetime(cv_last_modified, 'unixepoch', 'localtime') as modified_at
FROM cv_modification_timestamps
WHERE cv_last_modified > (strftime('%s', 'now') - 86400)
ORDER BY cv_last_modified DESC;
```

---

## Table: consist_state

**Purpose**: Store Virtual Mode and Auto Compensation state per consist

```sql
CREATE TABLE consist_state (
    consist_id INTEGER PRIMARY KEY,   -- 10 or 11
    virtual_mode BOOLEAN NOT NULL DEFAULT 1,
    auto_compensation_enabled BOOLEAN NOT NULL DEFAULT 1,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Example**:
```
consist_id: 11
virtual_mode: 1 (true)
auto_compensation_enabled: 1 (true)
last_updated: 2026-01-18 23:22:48
```

**Virtual Mode**:
- `true`: CV19=0 (software consist via z21-Terminal)
- `false`: CV19=consist_id (DCC consist)

---

## Table: system_state

**Purpose**: System-wide key-value state storage

```sql
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Example**:
```
key: "active_session_id"
value: "20260118_232248"
last_updated: 2026-01-18 23:22:48
```

---

## Common Queries

### Find all gate crossings for consist 11 in last 24h
```sql
SELECT
    datetime(timestamp, 'unixepoch', 'localtime') as time,
    json_extract(data, '$.delta_t') as delta_t,
    json_extract(data, '$.status') as status,
    json_extract(data, '$.speed') as speed
FROM events
WHERE event_type='delta_t'
  AND json_extract(data, '$.consist_id')=11
  AND timestamp > (strftime('%s', 'now') - 86400)
ORDER BY timestamp DESC;
```

### Get locomotive operating time summary
```sql
SELECT
    address,
    name,
    total_operating_seconds / 3600.0 as hours,
    total_sessions,
    datetime(last_active_time, 'unixepoch', 'localtime') as last_active
FROM locomotive_stats
ORDER BY total_operating_seconds DESC;
```

### Count events by type and session
```sql
SELECT
    session_id,
    event_type,
    COUNT(*) as count
FROM events
GROUP BY session_id, event_type
ORDER BY session_id DESC, count DESC;
```

### Find speed table modifications
```sql
SELECT
    loco_address,
    source,
    datetime(last_modified, 'unixepoch', 'localtime') as modified,
    cv67, cv68, cv69, cv94
FROM locomotive_speed_table
ORDER BY last_modified DESC;
```

---

## Common Queries

### Find all CRITICAL delta_t events for consist 11
```sql
SELECT datetime(timestamp, 'unixepoch', 'localtime') as time,
       json_extract(data, '$.delta_t') as delta_t,
       json_extract(data, '$.status') as status
FROM events
WHERE event_type='delta_t'
  AND json_extract(data, '$.consist_id')=11
  AND json_extract(data, '$.status')='CRITICAL'
ORDER BY timestamp DESC;
```

### Find all gate crossings for consist 11 (last 24h)
```sql
SELECT datetime(timestamp, 'unixepoch', 'localtime') as time,
       json_extract(data, '$.delta_t') as delta_t,
       json_extract(data, '$.status') as status,
       json_extract(data, '$.speed') as speed
FROM events
WHERE event_type='delta_t'
  AND json_extract(data, '$.consist_id')=11
  AND timestamp > (strftime('%s', 'now') - 86400)
ORDER BY timestamp DESC;
```

### Get locomotive operating time summary
```sql
SELECT address, name,
       total_operating_seconds / 3600.0 as hours,
       total_sessions
FROM locomotive_stats
ORDER BY total_operating_seconds DESC;
```

### Delete outlier delta_t events (|Δt| > 3s without speed)
```sql
DELETE FROM events
WHERE id IN (
  SELECT id FROM events
  WHERE event_type='delta_t'
    AND (json_extract(data, '$.delta_t') > 3.0 OR json_extract(data, '$.delta_t') < -3.0)
    AND json_extract(data, '$.speed') IS NULL
);
```

### Copy database between Mac and PC
```bash
# Mac → PC
scp backend/data/data.db user@hostname:C:/z21-Terminal/backend/data/data.db

# PC → Mac
scp user@hostname:C:/z21-Terminal/backend/data/data.db backend/data/data.db
```

---

## Maintenance

### Database size
```bash
ls -lh backend/data/data.db
```

### Vacuum (reclaim space after deletions)
```bash
sqlite3 backend/data/data.db "VACUUM;"
```

### Backup
```bash
cp backend/data/data.db backend/data/data.db.backup
```

### Count records
```sql
SELECT 'sessions' as table_name, COUNT(*) as count FROM sessions
UNION ALL
SELECT 'events', COUNT(*) FROM events
UNION ALL
SELECT 'locomotive_stats', COUNT(*) FROM locomotive_stats
UNION ALL
SELECT 'locomotive_speed_table', COUNT(*) FROM locomotive_speed_table
UNION ALL
SELECT 'consist_state', COUNT(*) FROM consist_state
UNION ALL
SELECT 'system_state', COUNT(*) FROM system_state;
```

---

## Migration History

- **2026-01-20**: Added decoder metadata to locomotive_speed_table (vstart, vhigh, decoder_type)
- **2026-01-20**: ESU mfx decoder support (CV67/CV94 read-only, CV2/CV5 endpoints)
- **2025-01-17**: Migrated from analytics.db → data.db (unified database)
- **2025-01-17**: Added locomotive_speed_table (CV67-94 storage)
- **2025-01-17**: Added consist_state (Virtual Mode tracking)
- **2025-01-17**: Migrated JMRI roster to config.json (locomotive functions)

See `docs/SPEED_TABLE_DB_MIGRATION.md` and `docs/SPEED_TABLE_DECODER_BEHAVIOR.md` for complete migration details.
