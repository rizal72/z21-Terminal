# Future Feature Ideas 💡

**Status**: Brainstorming - Ideas not prioritized or scheduled

Questa è una lista di possibili enhancements per z21-Terminal. Nessuna di queste è pianificata o in roadmap, sono solo spunti per future considerazioni.

---

## 📊 Analytics & Monitoring

### Session Statistics Dashboard
**Obiettivo**: Visualizzare metriche operative per analisi post-session

**Features**:
- Tempo totale operazione per consist
- Distanza percorsa (stima da gate crossings × lunghezza tracciato)
- Gate crossing counts per consist (quante volte hanno passato ogni gate)
- Speed profile heatmaps (velocità media per zone tracciato)
- Lap times (se tracciato chiuso, tempo per giro completo)

**UI**:
- Tab separato "Analytics" in dashboard
- Grafici real-time (Chart.js o similar)
- Session summary al termine operazioni

**Backend**:
- In-memory aggregation durante sessione
- Export JSON/CSV per analisi offline

---

### Δt Trends Visualization
**Obiettivo**: Monitorare efficacia speed compensation nel tempo

**Features**:
- Time-series graph di Δt per consist (ultimi 30 min, 1h, session completa)
- Color zones: Verde (SYNCED), Giallo (WARNING), Rosso (CRITICAL)
- Annotazioni automatiche: user speed changes, compensation events, mode toggles
- Statistics: tempo % in ogni zona, compensation count, average |Δt|

**Utilità**:
- Identificare se speed matching degrada nel tempo
- Decidere se serve Auto CV Adjust (Phase 8)
- Debugging compensation algorithm

---

### YOLO Performance Monitoring
**Obiettivo**: Verificare che detection quality rimanga alta nel tempo

**Features**:
- Real-time FPS monitoring (inference speed)
- Average confidence per loco (sliding window 1 min)
- Detection miss rate (frame con expected locos ma non detectati)
- Alert se confidence < 50% per più di 10s (possibile model degradation)

**Cause possibili degradazione**:
- Illuminazione cambiata (sole, ombre)
- Nuovi oggetti sul tracciato non nel training set
- Camera spostata/sfocata

**UI**:
- Small badge su video feed: "FPS: 28 | Conf: 0.87"
- Alert toast se detection quality drop

---

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

## 💾 Data Logging & Export

### Historical Session Database
**Obiettivo**: Persistere dati session per analisi long-term

**Stack**:
- SQLite database (`sessions.db`)
- Tables: `sessions`, `delta_t_events`, `gate_crossings`, `speed_changes`
- Automatic pruning (keep last 30 days, or configurable)

**Features**:
- Session list view (date, duration, consists used)
- Drill-down: click session → vedi tutti eventi
- Compare sessions (quale aveva Δt migliore?)

**Export**:
- CSV export per session (importabile in Excel, Python pandas)
- JSON export per backup completo

---

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

Queste idee NON sono in roadmap. Se in futuro servirà implementarne qualcuna, considerare:

1. **Quick wins** (1-2 giorni):
   - Session statistics dashboard (backend data già disponibile)
   - Δt trends visualization (Chart.js integration)
   - Autopilot gradual ramping (modify existing speed command logic)

2. **Medium effort** (3-5 giorni):
   - SQLite session history
   - Consist lock mechanism (WebSocket + backend state)
   - Decoder health monitoring (periodic CV read)

3. **Large projects** (1-2 settimane):
   - Session replay mode (requires full event logging + playback engine)
   - Virtual stations & routes (complex route planner UI)
   - Track Map integration (se Phase 7 postponed)

4. **External dependencies**:
   - Motor load monitoring (requires RailCom support)
   - Track power telemetry (requires Z21 Pro or similar)

---

**Ultimo aggiornamento**: 2025-01-08
