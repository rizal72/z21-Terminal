# Future Feature Ideas 💡

**Status**: Brainstorming - Ideas not prioritized or scheduled

This document lists potential enhancements for z21-Terminal. None of these are planned or in the roadmap—just ideas for future consideration.

---

## ✅ Already Implemented (Moved from Future)

The following features were in this document but have since been implemented:

### Session Statistics Dashboard ✅
**Status**: Implemented as **Analytics Dashboard** (2026-01-14)
- Hotkey `A` toggles Analytics panel
- Session tracking with lifecycle management
- Real-time statistics: Δt events, YOLO performance, locomotive operating time
- See [docs/ANALYTICS.md](ANALYTICS.md) for details

### Δt Trends Visualization ✅
**Status**: Implemented in **Analytics Tab** (2026-01-14)
- Time-series chart with color-coded zones (SYNCED/WARNING/CRITICAL)
- Current vs Overview views (last N events vs full session)
- Intelligent downsampling (LTTB + critical event preservation)
- Configurable `max_chart_events` via Settings UI

### YOLO Performance Monitoring ✅
**Status**: Implemented in **Analytics Tab** (2026-01-14)
- Real-time FPS chart with average FPS badge
- Per-locomotive confidence display
- Detection stats tracked in `data.db` (events table, event_type='yolo_performance')

### Historical Session Database ✅
**Status**: Implemented as **data.db** (2026-01-17)
- SQLite database with tables: sessions, events, locomotive_stats, locomotive_speed_table, consist_state
- Event types: delta_t, speed_setting, loco_operating_time, yolo_performance
- Auto-pruning not yet implemented (manual VACUUM for now)
- See [docs/DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for complete schema

---

## 📊 Analytics & Monitoring (Future)

## 🔔 Notifications & Alerts

### Telegram/Email Integration
**Obiettivo**: Notifiche remote per eventi critici

**Features**:
- **Derailment detection**: Nessun gate crossing per X minuti (consist fermo/deraiato)
- **Critical Δt alert**: |Δt| > 2.0s per più di 30s (speed matching fallito)
- **Backend crash**: Service restart notifications
- **Track power loss**: Z21 segnala power off inatteso

**Setup**:
- Config: Telegram bot token + chat ID (o SMTP settings per email)
- UI: Enable/disable notifications per event type
- Test notification button

**Privacy**:
- Credentials in `config.local.json` (gitignored)
- Optional feature (disabled by default)

---

### Mobile Push Notifications
**Obiettivo**: PWA notifications su smartphone

**Features**:
- Browser Push API (service worker)
- Notifiche anche quando dashboard non in foreground
- Vibrazione per eventi critici (mobile)

**Use case**:
- User allontanato dal plastico ma vuole essere avvisato di problemi
- Multi-tasking (dashboard in background, notification pop-up)

---

## 💾 Data Logging & Export (Future)

### Session Replay Mode
**Obiettivo**: Visualizzare session passate come se fosse live

**Features**:
- Time slider (scrub through session timeline)
- Play/Pause controls
- Speed controls (1x, 2x, 5x replay)
- Overlay Δt panel + locomotive positions (se Track Map implementata)

**Use case**:
- Debugging: "cosa è successo quando Δt è saltato a +3.0s?"
- Training: mostrare ad altri come funziona Virtual Mode
- Analisi: confrontare before/after tuning

---

## 🎮 Advanced Control Features

### Autopilot Mode
**Obiettivo**: Automated speed control con ramping graduale

**Features**:
- **Gradual acceleration**: Invece di 0→60 istantaneo, rampa progressiva (10 step/sec)
- **Gradual deceleration**: Smooth stop (no jerk)
- **Configurable profiles**: "Aggressive" (fast ramp), "Smooth" (slow ramp), "Realistic" (simula inerzia treno)

**UI**:
- Toggle "Autopilot" per consist
- Speed target slider (autopilot raggiunge target gradualmente)
- Profile selector dropdown

**Benefits**:
- Più realistico (treni veri non accelerano istantaneamente)
- Riduce stress meccanico su ingranaggi
- Migliore estetica operazioni

---

### Virtual Stations & Scheduled Stops
**Obiettivo**: Gate-based triggers per stop automatici

**Setup**:
- Assign gates as "stations" (e.g., Gate 1 = "Stazione Centrale")
- Route planning: "Consist 11 → stop at Gate 1 for 10s → continue to Gate 2"

**Features**:
- Automatic stop quando loco passa gate-station
- Timer countdown (10s wait)
- Automatic resume a velocità precedente
- UI: Route builder (drag-drop gates in sequence)

**Use case**:
- Operazioni simulate (pickup/drop passeggeri)
- Demo mode (show visitors automatic operations)
- Stress test (cycle consist around track for hours)

---

### Speed Limit Zones
**Obiettivo**: Auto-throttle basato su posizione tracciato

**Setup**:
- Define zones via gates (e.g., "Between Gate 1 and Gate 2 = max 30%")
- YOLO position → determina zona corrente → enforce limit

**Features**:
- Speed cap per zone (UI warning se user prova superare)
- Automatic slow-down quando entra zona limitata
- UI: Zone visualizer su Track Map (se implementata)

**Use case**:
- Safety: curve strette = speed limit
- Realism: tunnel = slow down
- Prevent derailment: zone problematiche = cautela

---

## 👥 Multi-User Features

### Consist Lock Mechanism
**Obiettivo**: Prevent control conflicts con multiple devices

**Problema**:
- User A (iPad) controlla Consist 11
- User B (Phone) prova controllare Consist 11
- Conflict: chi ha controllo?

**Soluzione**:
- Backend lock system: 1 consist = 1 controller owner
- UI: "Consist locked by User A's iPad" (altri vedono read-only)
- Auto-release dopo inattività (5 min timeout)
- Force unlock (admin override)

**WebSocket protocol**:
```json
{
  "type": "lock_consist",
  "consist_address": 11,
  "user_id": "ipad-uuid"
}
```

---

### Session Sharing (QR Code)
**Obiettivo**: Easy onboarding per nuovi users

**Flow**:
1. Host genera QR code su dashboard
2. Guest scanna QR → apre URL con session token
3. Guest vede stessa dashboard (WebSocket sync)
4. Guest può controllare consists non locked

**UI**:
- "Share Session" button in header
- Modal con QR code + URL copiabile
- Guest badge su client list (distingui host vs guests)

**Security**:
- Session tokens temporanei (expire dopo 24h)
- Optional password protection

---

### Spectator Mode
**Obiettivo**: View-only access per visitors

**Features**:
- Read-only dashboard (no controls, solo visualizzazione)
- Vede video feed + Δt stats + locomotive positions
- No login required (public URL)

**Use case**:
- Live streaming operations (YouTube/Twitch con embedded dashboard)
- Remote monitoring senza rischio comandi accidentali
- Educational: studenti vedono senza toccare

---

## 🔧 Maintenance & Diagnostics

### CV3/CV4 Acceleration/Deceleration Editor ⚡ Quick Win
**Obiettivo**: UI editing per CV3 (Acceleration) e CV4 (Deceleration) in config.json senza JMRI

**Situazione attuale**:
- CV3/CV4 hardcoded in `config.json` → `locomotives.X.cv_profiles.normal` e `locomotives.X.cv_profiles.testing`
- Toggle TEST/NORMAL (hotkey `T`) scrive i valori da config al decoder
- Modifica dei valori richiede: JMRI + edit manuale config.json

**Why now**:
- Durante speed table tuning lavoriamo con momentum off (CV3=CV4=0)
- Quando attiveremo accel/decel, il tuning speed table potrebbe essere influenzato
- Serve poter testare diversi valori CV3/CV4 rapidamente

**UI Proposta**: Settings > Locomotives tab
- Sotto ogni accordion loco, **PRIMA della lista functions**, aggiungi:
  ```
  ┌─ Locomotive: Gr.675 017 (Address 1) ────────────────┐
  │                                                      │
  │ [Acceleration/Deceleration - Normal Mode]           │
  │ CV3 (Accel):  [12] ✏️  (inline edit, 0-255)        │
  │ CV4 (Decel):  [8]  ✏️  (inline edit, 0-255)         │
  │                                                      │
  │ Note: Values applied when you press T (toggle mode) │
  │ Test mode always uses CV3=CV4=0                     │
  │                                                      │
  │ ─────────────────────────────────────────────────── │
  │                                                      │
  │ [Functions]                                          │
  │ F0: Light     [Lockable ☐]                          │
  │ F1: Sound     [Lockable ☑]                          │
  │ ...                                                  │
  └──────────────────────────────────────────────────────┘
  ```
- **Ordine UI**: CV3/CV4 section → Separator → Functions list
- Modifica CV3/CV4 → **Salva solo in config.json** (NON scrive al decoder)
- I valori vengono applicati al decoder **solo quando si fa toggle TEST/NORMAL** (hotkey `T`)

**Workflow**:
1. User edita CV3/CV4 in Settings → Salva in config.json (normal profile)
2. User preme hotkey `T` → Toggle TEST/NORMAL → **A quel punto** scrive CV3/CV4 al decoder
3. I valori editati sono attivi **solo in NORMAL mode** (test mode sempre CV3=CV4=0)

**Infrastruttura già pronta**:
- ✅ Toggle TEST/NORMAL già legge da config e scrive CV3/CV4 al decoder
- ✅ Config save/reload già funziona (`/api/settings/update`)
- ✅ Settings UI già supporta inline editing (vedi Functions tab)
- ❌ Manca solo: UI input fields per CV3/CV4 (puro frontend)

**Complessità**: ~1-2 ore (solo frontend, nessun backend nuovo)

**Alternative location**: Speed Table Viewer (insieme a Vstart/Vhigh ESU)
- **Scartato**: Settings > Locomotives è più logico (CV3/CV4 sono proprietà della loco, non specifici del speed table)

---

### Decoder Health Monitoring
**Obiettivo**: Detect CV drift o malfunzionamenti decoder

**Features**:
- Periodic CV read (CV2, CV5, CV19, CV29) ogni 1h
- Compare con baseline (salvato in `decoder_baseline.json`)
- Alert se valore cambia (possibile corruption o reset decoder)

**UI**:
- "Decoder Health" tab per locomotive
- Green checkmark se OK, Yellow warning se drift, Red se failed read
- "Restore from Baseline" button (re-write CV)

**Use case**:
- Detect decoder reset (CV tornati a default)
- Track decoder reliability (ESU vs Hornby vs Zimo stats)

---

### Function Test Mode
**Obiettivo**: Verify decoder risponde a tutti i function commands

**Flow**:
1. Select locomotive
2. Click "Test Functions"
3. App cicla F0-F28 (1s on, 1s off per funzione)
4. User verifica manualmente (luci accendono, suoni funzionano, etc.)
5. Mark quale funzioni NON funzionano

**Output**:
- Report: "Loco 7: F0 ✓, F1 ✓, F2 ✗ (no response), F3 ✓, ..."
- Save report per troubleshooting

---

### Motor Load Monitoring
**Obiettivo**: Detect mechanical issues (ingranaggi sporchi, attrito)

**Prerequisiti**:
- Decoder supporta RailCom load telemetry
- Z21 espone load data via API (non tutti i decoders/Z21 supportano)

**Features**:
- Real-time motor current monitoring
- Alert se current spike (possibile binding, detrito su binari)
- Trend: current aumenta nel tempo = lubrificazione necessaria

**UI**:
- Small graph: motor load over time
- Warning icon se anomalie

---

### Track Power Quality Monitoring
**Obiettivo**: Detect problemi alimentazione binari

**Prerequisiti**:
- Z21 espone voltage/current telemetry (alcuni modelli lo supportano)

**Features**:
- Real-time track voltage/current display
- Alert se voltage drop (resistenza binari, ossidazione)
- Alert se current spike (short circuit risk)

**Use case**:
- Preventive maintenance: pulisci binari quando voltage cala
- Troubleshooting: derailment detection via current spike

---

### Automatic CV Backup/Restore
**Obiettivo**: Safety net prima di CV experiments

**Features**:
- "Backup All CVs" button per locomotive
  - Read CV 1-256 (se decoder supporta), save to `cv_backups/loco_7_2025-01-08.json`
- "Restore from Backup" button
  - Select backup file → re-write tutti CV
- Auto-backup prima di Auto CV Adjust (Phase 8) execution

**UI**:
- Backup list per loco (date, size, notes)
- Compare backups (show diff tra 2 backup files)

**Use case**:
- Experimenting con CV: backup → test → restore se non va
- Disaster recovery: decoder reset accidentale

---

## Prioritization Notes

These ideas are NOT in the roadmap. If any are needed in the future, consider:

1. **Quick wins** (1-2 days):
   - Telegram/Email notifications (backend already has session/tracking events)
   - Autopilot gradual ramping (modify existing speed command logic)
   - Function Test Mode (cycle F0-F28 with existing commands)

2. **Medium effort** (3-5 days):
   - Session Replay Mode (requires playback engine for stored events)
   - Consist lock mechanism (WebSocket + backend state)
   - Decoder health monitoring (periodic CV read)
   - CSV/JSON export for sessions (data.db already structured)

3. **Large projects** (1-2 weeks):
   - Virtual stations & routes (complex route planner UI)
   - Track Map integration (if Phase 7 resumed)
   - Spectator mode with authentication

4. **External dependencies**:
   - Motor load monitoring (requires RailCom support)
   - Track power telemetry (requires Z21 Pro or similar)

---

**Last Updated**: 2026-01-20
