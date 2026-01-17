# Computer Vision Tracking System

**Status**: 🚀 Phase 4 Complete - Gate Timing Detection Operational  
**Project**: z21-Terminal - BiancAlice Railway Layout

YOLO-based locomotive tracking system with dual-gate timing detection for automatic speed matching and consist synchronization.

---

## Computer Vision Tracking System

**Status**: 🚀 **RIPRESA CON YOLO** (decisione 2025-12-29 sera - approccio ML scelto)

### Obiettivo
Sistema di tracking locomotive via webcam per:
- **Monitoraggio posizioni real-time** delle locomotive sul tracciato
- **Speed matching automatico** - rilevare drift velocità tra lead/rear
- **Auto-calibrazione consist** via CV adjustment (Mode 2)

### Approccio: Timing-Based Gate Crossing

**⚠️ STRATEGIA POST-REFACTOR** (2025-12-30): Abbandono distance monitoring, adozione timing-based detection

**Perché timing-based?**
- Distance-based funziona solo per tracciati semplici (C11: 3% co-visibility)
- C10 tracciato complesso (figura 8): 0.5% co-visibility - INSUFFICIENTE
- Timing detection più affidabile: non richiede entrambe le loco visibili contemporaneamente

**Consist 11** (tracciato esterno - ovale):
```
                  Gate 2 - LONTANO (top left)
                  ╔════════════╗
         ┌────────║ 60x60px    ║────────┐
         │        ║ (141, 162) ║        │
         │        ╚════════════╝        │
         │                              │
         │      ENTRAMBE LE LOCO        │
         │      attraversano            │
    Oval track  ENTRAMBI i gate    Oval track
         │      durante il giro         │
         │                              │
         │        ╔═════════════╗       │
         └────────║  100x100px  ║───────┘
                  ║ (1227, 293) ║
                  ╚═════════════╝
                  Gate 1 - VICINO (bottom right)
```

- **2 gate rettangolari CONDIVISI** (entrambe le loco attraversano entrambi i gate)
  - **Gate 1 (VICINO)**: bottom right, 100x100px, center (1227, 293)
    - Più grande perché area detection più affidabile (vicino camera)
  - **Gate 2 (LONTANO)**: top left, 60x60px, center (141, 162)
    - Più piccolo perché zona detection già molto accurata
  - **Perché 2 gate**: entrambe le loco attraversano entrambi durante il giro completo
- **Co-presence timing detection con cross-validation**:
  - **Gate 1**: Δt₁ = timestamp_loco7_gate1 - timestamp_loco8_gate1
  - **Gate 2**: Δt₂ = timestamp_loco7_gate2 - timestamp_loco8_gate2
  - **Baseline**: Δt₁ ≈ Δt₂ ≈ 0 (sincronizzazione perfetta su entrambi i gate)
  - **Cross-validation**: drift confermato solo se visto in ENTRAMBI i gate
- **Drift detection tramite chi passa per primo**:
  - **Δt > 0** (loco 7 passa prima) → loco 7 troppo veloce
  - **Δt < 0** (loco 8 passa prima) → loco 7 troppo lenta
  - |Δt| aumenta → desincronizzazione in corso
- **Check MOLTO frequente**: 4 crossing per giro completo
  - Loco 7: attraversa gate 1, poi gate 2
  - Loco 8: attraversa gate 1, poi gate 2
  - = 4 timestamp per giro = 2 valori Δt per confronto
- **Vantaggi strategia 2 gate condivisi**:
  - ✅ Check più frequente (doppi rispetto a 1 gate per loco)
  - ✅ Cross-validation anti-false-positive
  - ✅ Drift confermato se |Δt₁| e |Δt₂| entrambi sopra soglia
  - ✅ Anomalia rilevabile se solo 1 gate mostra drift (possibile problema detection)
  - ✅ **ROBUSTEZZA a YOLO detection intermittente** (CRITICO!):
    - Gate separati: servono 2 detection contemporanee → Δt mancante se 1 loco non detectata
    - Gate condivisi: 4 opportunità per giro → Δt calcolabile se almeno 1 gate funziona
    - Probabilità Δt valido MOLTO più alta (detection non sempre perfetta)

**Consist 10** (tracciato interno - figura 8):
- **2 gate configurati** - gate_ids: [3, 4] ✅ (G3: 1086,326 80x80px, G4: 479,29 50x50px)
- **⚠️ ASYMMETRIC MODE** (geometria figura-8 asimmetrica):
  - `gate_assignment: {reference: 3, adjust: 4}` in config.json
  - **Calcola SOLO**: L5@G3-L1@G4 (~0.5s quando sincronizzato)
  - **Ignora**: L1@G3-L5@G4 (~-18s sempre invalido per geometria tracciato)
  - **Motivo**: gate NON a metà esatta del percorso (impossibile su figura 8)
- **Check frequente**: 2 crossing per giro (1 valore Δt valido per giro)
- **Reference strategy**: L5 (D645 014 ESU) reference, L1 (Gr.675 017 ESU LokSound) adjust

**Scopo Drift Monitoring** (invariato):
- 🚨 **SICUREZZA ANTI-TAMPONAMENTO** - evitare collisione tra locomotive
  - **RISCHIO BIDIREZIONALE** su tracciato circolare
  - Rear troppo veloce O lead troppo veloce → DERAGLIAMENTO 💥
- 🎯 **Speed matching** - mantenere formazione consistente
- 🎯 **Rilevare desincronizzazione** prima che diventi evidente
- 🎯 **Auto-adjust CV** per correggere deriva velocità (Mode 2)

**Soglie Timing Co-presence** (da stabilire con testing):
- **Baseline**: Δt ≈ 0s (passaggio quasi contemporaneo)
- **Warning**: |Δt| > 0.5s (lieve desincronizzazione)
- **Critical**: |Δt| > 1.0s (desincronizzazione evidente)
- **Emergency**: |Δt| > 2.0s (intervento automatico richiesto)

### ⚙️ Reference Loco Strategy (CRITICO per Auto CV Adjust)

**Problema reale C11**:
- **Loco 7 (E656_239, lead)**: Decoder Hornby TXS, comportamento **instabile**
  - Speed table regolata step-by-step manualmente per matchare loco 8
  - Risposta velocità meno prevedibile
- **Loco 8 (E444_056, rear)**: Decoder ESU LokPilot 5, comportamento **stabile**
  - Speed table lineare costante (match ends Vmin-Vmax)
  - Curva velocità perfetta e prevedibile

**Decisione per Mode 2 Auto CV Adjust**:
- **Reference loco**: **Loco 8 (rear)** ← quella con decoder stabile (ESU)
- **Adjust loco**: **Loco 7 (lead)** ← quella con decoder instabile (Hornby)
- **Mai toccare** i CV della loco 8 (curva perfetta da preservare)
- **Sempre aggiustare** i CV della loco 7 per matchare la loco 8

**Logica adjustment C11**:
- Δt > 0 (loco 7 passa prima) → loco 7 troppo veloce → **rallenta loco 7** (aumenta CV2/CV5)
- Δt < 0 (loco 8 passa prima) → loco 7 troppo lenta → **accelera loco 7** (diminuisci CV2/CV5)
- **Obiettivo**: Δt → 0 (sincronizzazione perfetta)

**Per C10** (✅ confermato 2025-01-07):
- **Reference loco**: **Loco 5 (D645 014, rear)** ← ESU LokPilot 5, decoder stabile
- **Adjust loco**: **Loco 1 (Gr.675 017, lead)** ← ESU LokSound, da compensare
- Stesso pattern C11: rear (ESU stabile) come reference, lead da aggiustare
- Decisione basata su decoder similarity (ESU standard più affidabile di ESU LokSound)

### Stack Tecnologico

**Computer Vision**:
- **OpenCV** (cv2) - Frame analysis e position tracking
- **YOLO o MobileNet** - Object detection per identificare locomotive
- **Python multiprocessing** - Processing video in background thread

**Hardware**:
- Webcam USB o IP camera
- Angolazione: top-down (vista dall'alto ottimale)
- Illuminazione consistente (critico per CV)

**Integration**:
- WebSocket stream posizioni → FastAPI backend → React frontend
- Video overlay con markers locomotive real-time

### ⚠️ CRITICAL: DCC Address as YOLO Class Prefix

**Convenzione Naming Classi YOLO**:
```
1_Gr675_017   # DCC Address 1 → Class prefix
5_D645_014    # DCC Address 5 → Class prefix
7_E656_239    # DCC Address 7 → Class prefix
8_E444_056    # DCC Address 8 → Class prefix
```

**REGOLA ASSOLUTA**: ❌ **MAI cambiare DCC address (CV1) dopo training YOLO**

**Perché è critico**:
- YOLO impara i nomi delle classi durante training (embedded in `best.pt`)
- Il codice mappa class ID → DCC address tramite il prefisso
- Cambiare CV1 rompe completamente il mapping:
  - YOLO detecta `7_E656_239` ma locomotiva ha address 9
  - Z21 non trova loco address 7 (non esiste più)
  - Consist mapping completamente rotto

**Se devi cambiare CV1**:
1. Rinominare classe su Roboflow (`7_E656_239` → `9_E656_239`)
2. Re-training completo da zero (nomi classi cambiati)
3. Deploy nuovo modello
4. Aggiornare codice Python con nuovo mapping
5. ⏱️ Tempo totale: ~2-3 ore lavoro

**Address permanenti** (NON toccare):
- ✅ Consist 10: Address 1, 5 (fissi per YOLO)
- ✅ Consist 11: Address 7, 8 (fissi per YOLO)
- 🆓 Liberi per future loco: 2, 3, 4, 6, 9+
- 🔒 Riservati consist: 10, 11

### Tre Modalità Operative

#### **Mode 1: Monitor Only** 📊
- Solo visualizzazione co-presence timing Δt tra lead/rear
- Sistema NON interviene automaticamente
- Alert visivi graduali (co-presence timing):
  - 🟢 "Δt = +0.3s ✓" (normale, |Δt| < 0.5s)
  - 🟡 "Δt = -0.8s - loco 7 rallenta" (warning, |Δt| 0.5-1.0s)
  - 🔴 "Δt = +1.5s - PERICOLO DESYNC!" (critical, |Δt| > 1.0s)
- **Sign Δt indica chi è più veloce**:
  - Δt > 0 (loco 7 passa prima) → loco 7 troppo veloce
  - Δt < 0 (loco 8 passa prima) → loco 7 troppo lenta
- Utente decide se/quando aggiustare manualmente CV tramite JMRI
- **Scopo**: Rilevare desincronizzazione per sicurezza + speed matching

#### **Mode 2: Auto CV Adjust** 🤖 (RACCOMANDATO)
- **Operations Mode CV Write** - aggiusta CV mentre locomotive stanno circolando!
- Mantiene Δt ≈ 0 automaticamente (sincronizzazione perfetta)
- CV aggiornati permanentemente nei decoder (mantengono sync dopo power cycle)
- Safety: max ±5 adjust/session, cooldown 30sec, confirmation UI
- **Reference Loco Strategy**:
  - **Consist 11**: Mai toccare loco 8 (ESU stabile), aggiusta sempre loco 7 (Hornby)
  - **Consist 10**: Aggiusta loco meno stabile (da determinare)
- **Intervento basato su sign Δt**:
  - Δt > 0 (loco 7 troppo veloce) → rallenta loco 7 (aumenta CV)
  - Δt < 0 (loco 7 troppo lenta) → accelera loco 7 (diminuisci CV)
- **Scopo**: Sicurezza anti-tamponamento + speed matching automatico

**Vantaggi Z21 Operations Mode**:
- ✅ Nessun programming track necessario
- ✅ Loco può continuare a circolare
- ✅ Adjustment incrementale testabile al volo
- ✅ CV permanenti (mantengono sync dopo power cycle)
- ✅ Compatible con JMRI consist

**Adjustment speeds**:
- Conservative: 1 step CV ogni 5min
- Moderate: 1 step CV ogni 2min
- Aggressive: 1 step CV ogni 30sec

#### **Mode 3: Software Sync** ⚡
- Loco separate (NO consist DCC)
- Dual control real-time con speed compensation
- Non scrive CV (temporaneo, solo durante sessione)
- Use case: testing rapido, demo, situazioni dove consist DCC non funziona

### Z21 Operations Mode Write

**XpressNet command**: `0xE6 0x30` (Operations Mode Byte Write)

```python
def write_cv_ops_mode(self, address, cv_number, cv_value):
    """
    Write CV in operations mode (locomotive on main track).
    Works while locomotive is running!
    """
    # Implementation: XpressNet E6 30 [addr] [cv] [value] [xor]
```

**⚠️ NOTA CRITICA**: Z21 White NON supporta CV READ in operations mode (testato 2025-12-17), ma CV WRITE dovrebbe funzionare (da testare prima di procedere).

### UI Features

**Pannelli dinamici**:
- Pulsante `[+]` in alto dx per aggiungere controller
- Supporto N controller (non solo 2)
- Rimozione panel con `[×]`
- Scroll orizzontale responsive

**CV Tracking Panel** (mockup co-presence timing dual-gate - IMPLEMENTATO 2025-12-30):
```
┌─────────────────────────────────────────────┐
│ ⏱️ Gate Timing (Consist 11)                 │
│ Mode: [Monitor Only ▼]  (future)          │
├─────────────────────────────────────────────┤
│ Gate 1 (VICINO - 100x100px):               │
│   Loco 7: 12:34:56  ● (0.87)               │
│   Loco 8: 12:34:57  ● (0.84)               │
│   Δt₁ = +0.300s  🟢 SYNCED                  │
│                                             │
│ Gate 2 (LONTANO - 60x60px):                │
│   Loco 7: 12:35:02  ● (0.82)               │
│   Loco 8: 12:35:03  ● (0.79)               │
│   Δt₂ = +0.276s  🟢 SYNCED                  │
│                                             │
│ 📊 Cross-Validation (future):              │
│ |Δt₁ - Δt₂| = 0.024s  ✅ CONSISTENT        │
│ Average Δt = +0.288s  🟢 SYNCED             │
│ (Loco 7 passa ~0.3s prima - normale)       │
│                                             │
│ 🚨 Δt THRESHOLDS (implemented):            │
│ 🟢 |Δt| < 0.5s   SYNCED                     │
│ 🟡 |Δt| 0.5-1.0s WARNING                    │
│ 🔴 |Δt| > 1.0s   CRITICAL DESYNC            │
│                                             │
│ History (last 10 crossings) - future       │
│ G1: ━━━━━━━━━━━━━━━ +0.29s avg             │
│ G2: ━━━━━━━━━━━━━━━ +0.27s avg             │
│                                             │
│ ⚙️ Reference: Loco 8 (ESU stable)           │
│ 🔧 Adjust: Loco 7 (Hornby)                  │
│                                             │
│ [Mode: Monitor/Auto/Software]  (future)   │
│ [Reset] [History] [EMERGENCY STOP]         │
└─────────────────────────────────────────────┘
```

**Note Panel**:
- **Dual-gate co-presence timing** - 2 gate condivisi, entrambe le loco attraversano entrambi
  - **Gate 1 (VICINO)**: center (1227, 293), 100x100px, bottom right - sempre più vicino camera
  - **Gate 2 (LONTANO)**: center (141, 162), 60x60px, top left - sempre più lontano camera
  - **Nomenclatura fissa**: numerazione per posizione fisica, NON per locomotiva
- **Misure per gate**:
  - Δt₁ = timestamp_loco7_gate1 - timestamp_loco8_gate1
  - Δt₂ = timestamp_loco7_gate2 - timestamp_loco8_gate2
- **Cross-validation** (future): |Δt₁ - Δt₂| < threshold per conferma drift
- **Color coding Δt** (✅ implemented): 🟢 |Δt|<0.5s (SYNCED), 🟡 0.5-1.0s (WARNING), 🔴 >1.0s (CRITICAL)
- **Sign Δt indica chi passa per primo** (✅ implemented):
  - Δt > 0 → loco 7 passa prima (troppo veloce)
  - Δt < 0 → loco 8 passa prima (loco 7 troppo lenta)
- **Reference loco strategy**: loco 8 mai toccata, adjust sempre loco 7
- **Baseline da stabilire** con testing (media ultimi 10 crossings)
- **Check frequency**: 4 crossing per giro (2 per loco) - molto robusto
- **Console logging**: emoji 🚪 quando Δt calcolato
- **History graph** (future) mostra trend Δt₁ e Δt₂ su ultimi crossings
- **Emergency stop button** (future) per intervento manuale su |Δt| > 2.0s

### Roadmap Implementazione

#### **Phase 1: UI Scalabile** ✅ COMPLETATA (2025-12-29)
- [x] Pulsante [+] add controller
- [x] State management controllers array
- [x] Panel dinamici con rimozione `[×]`
- [x] Auto-scroll al nuovo pannello
- [x] Multi-device sync via WebSocket
- [ ] Mode selector UI (Monitor/Auto/Software) - rimandato a Phase 3+

#### **Phase 2: Z21 OPS Write/Read** ✅ **COMPLETATA** (2025-12-29)
- [x] **CV WRITE implementato**: `write_cv_ops_mode()` in z21.py
  - Comando: `E6 30 [addr] [EC|cv_msb] [cv_lsb] [value] [xor]`
  - Test: CV4 cambiato 14→20→14 ✅
  - Decoder: ESU + Hornby funzionanti
- [x] **CV READ implementato**: `read_cv_on_main()` in z21.py
  - Comando: `E6 30 [addr] [E4|cv_msb] [cv_lsb] [0x00] [xor]` (verify trick)
  - Risposta: `64 14 [addr] [VALUE] [xor]`
  - Test: CV4 letto = 14 (primo tentativo) ✅
  - **CRITICO**: Funziona SOLO su decoder ESU, NON su Hornby TXS
- [x] **Mode 2 (Auto CV Adjust)**: ✅ CONFERMATO FATTIBILE
- [x] **Tool utility**: `read_cv_from_roster.py` mostra TUTTI i CV (non solo speed)

#### **Phase 3: CV Tracking Setup** ✅ **COMPLETATA** (2025-12-30)
- [x] OpenCV setup e webcam capture - Tapo IP camera RTSP 720P funzionante
- [x] Webcam locale: IP camera acquario testata con successo
- [x] Object detection (YOLO custom trained) - ✅ **Model v5 active** (2025-01-05)
  - YOLOv8 nano trained su 4 locomotive (mAP50 = **0.931** - best model)
  - Square 640x640 optimization for fast CPU inference
  - Detection real-time tutte e 4 classi con confidence 0.60-0.92
  - Inference size configurable via `config.json` → `tracking.yolo_imgsz: 640`
  - Pannello "All Locomotives Detected" con indicators colorati
  - Console logging intelligente (immediate + periodic summary)
  - Model history: v3 (80.7%), v4 rectangular (91.9%), v5 square (93.1% ✅)
- [x] Distance calculation real-time - 30 samples raccolti, 909.7px average
- [x] ~~Calibrazione pixel-to-cm ratio~~ - **NON NECESSARIA**
  - **Decisione**: usare pixel direttamente per drift monitoring
  - **Motivo**: camera grandangolo con distorsione fish-eye
  - Pixel/cm varia con distanza dalla camera (17 px/cm vicino vs ~8-10 lontano)
  - Lead+rear sempre alla stessa distanza → rapporto px/cm uguale per entrambe
  - Drift rilevabile comparando variazioni in pixel (es. 909px baseline)

#### **Phase 4: Timing-Based Gate Crossing Detection** ✅ **COMPLETATA** (2025-12-30)
**Strategia**: Co-presence timing con 2 gate rettangolari CONDIVISI + cross-validation

**Status**: ✅ Core detection implementato per Consist 11.
**Remaining**: Video performance optimization + Generic refactor per supporto multi-consist.

**Consist 11** (tracciato esterno - ovale):
- [x] **Definire 2 gate rettangolari CONDIVISI** (entrambe le loco attraversano entrambi) ✅
  - **Gate 1 (VICINO)**: center (1227, 293), 100x100px, bottom right - sempre il più vicino alla camera
  - **Gate 2 (LONTANO)**: center (141, 162), 60x60px, top left - sempre il più lontano dalla camera
  - Rettangolari per compensare detection YOLO intermittente
  - Hardcoded coordinates da marker mode test (2025-12-30)
  - **Nomenclatura**: Gate 1 e 2 (NON "gate lead/rear"), numerate per posizione fissa
- [x] **Implementare dual-gate crossing detection** ✅
  - Trigger: quando loco entra in ciascuna gate zone (point-in-polygon test)
  - Record 4 timestamp per giro:
    - timestamp_loco7_gate1, timestamp_loco7_gate2
    - timestamp_loco8_gate1, timestamp_loco8_gate2
  - Calcola 2 valori Δt:
    - **Δt₁ = timestamp_loco7_gate1 - timestamp_loco8_gate1**
    - **Δt₂ = timestamp_loco7_gate2 - timestamp_loco8_gate2**
  - Rising edge detection: timestamp salvato solo quando loco ENTRA nel gate
- [x] **Drift detection tramite co-presence timing** ✅
  - Baseline: **Δt₁ ≈ Δt₂ ≈ 0** (sincronizzazione perfetta su entrambi)
  - Soglie implementate: ±0.5s (green SYNCED), 0.5-1.0s (yellow WARNING), >1.0s (red CRITICAL)
  - **Chi passa per primo** indica chi è più veloce:
    - Δt > 0 → loco 7 (lead) passa prima → troppo veloce
    - Δt < 0 → loco 8 (rear) passa prima → loco 7 troppo lenta
  - **Cross-validation**: da implementare nella UI (attualmente mostra Δt₁ e Δt₂ separati)
  - Check MOLTO frequente: 4 crossing per giro (2 per loco)
  - Console logging: emoji 🚪 con Δt quando calcolato
- [x] **UI panel co-presence timing stats dual-gate** ✅
  - **Gate 1 (VICINO - 100x100px)**: timestamp loco 7 + loco 8, Δt₁ con color coding
  - **Gate 2 (LONTANO - 60x60px)**: timestamp loco 7 + loco 8, Δt₂ con color coding
  - Color coding implementato: verde |Δt|<0.5s (SYNCED), giallo 0.5-1.0s (WARNING), rosso >1.0s (CRITICAL)
  - Sign Δt visualizzato con formato `+0.123s` o `-0.456s`
  - Gate disegnati sempre visibili: cyan/yellow (G1), orange (G2)

**Consist 10** (tracciato interno - figura 8):
- [x] **Definiti 2 gate condivisi** ✅ (2025-01-07 - asymmetric mode implementato)
  - **Gate 3**: center (1086, 326), 80x80px, cyan [0,255,255]
  - **Gate 4**: center (479, 29), 50x50px, cyan [0,255,255]
  - **⚠️ GEOMETRIA ASIMMETRICA**: gate NON a metà esatta percorso (figura-8 constraint)
- [x] **Asymmetric gate timing implementato** ✅
  - Config: `gate_assignment: {reference: 3, adjust: 4}`
  - **Calcola SOLO**: `Δt = L5@G3 - L1@G4` (direzione valida ~0.5s)
  - **Ignora completamente**: L1@G3-L5@G4 (~-18s sempre invalido)
  - Rising edge detection: timestamp quando loco entra nel gate
  - Console log: `🚪 C10 Asymmetric: L5G3-L1G4 = Δt = +0.347s`
- [x] **Drift detection tramite single-direction timing** ✅
  - Baseline: **Δt ≈ 0s** (sincronizzazione perfetta)
  - Soglie: <1.0s SYNCED, 1.0-1.5s WARNING, >1.5s CRITICAL
  - Chi passa per primo indica chi è più veloce (stesso logic C11)
  - Check frequente: 1 valore Δt valido per giro (2 crossing totali)

**Implementazione comune**:
- [ ] Gate zone detection con perspective-corrected coordinates
- [ ] Timestamp recording con precision millisecond
- [ ] Moving average lap times (ultimi 5-10 giri)
- [ ] WebSocket stream timing stats per Web Dashboard
- [ ] Audio alerts su drift critico
- [ ] Log eventi con severity (CRITICAL/WARNING/INFO)

---

### ✅ Phase 4 Completion Tasks (COMPLETED 2025-01-03)

#### **Task 4.1: Video Performance Optimization** ✅ **COMPLETED** (2025-01-01 → 2025-01-03)
**Problema**: Video freeze 1s+ quando entrambe le loco attraversano gate e Δt viene calcolato/aggiornato.

**Root cause**: Dual `cv2.VideoCapture` RTSP contention
- `tracking_daemon.py` + `video_feed.py` leggevano STESSO stream RTSP
- Camera Tapo buffering → 2 client concorrenti → lag inaccettabile

**Soluzione**: Frame Queue Sharing Architecture
- Single VideoCapture in daemon (producer)
- `asyncio.Queue(maxsize=2)` for frame buffering
- Video feed reads from queue (consumer)
- TrackingManager refactored: subprocess → asyncio.Task (shared memory)

**Status**: ✅ **COMPLETED & TESTED**
- ✅ Code implemented (commit `928d022`)
- ✅ User tested: Video NO LONGER freezes during Δt calculation
- ✅ Performance verified: Smooth video feed con gate crossing detection

**Files modified**:
- `backend/tracking_daemon.py` - Added frame queue producer + refactored to use `backend/tracking/` modules
- `backend/video_feed.py` - Converted to async queue consumer
- `backend/main.py` - Wired frame_queue from daemon to video endpoint
- `backend/tracking_manager.py` - Refactored subprocess → asyncio.Task

**Note**: Tracking daemon è stato successivamente refactored (2026-01-06) per estrarre logica condivisa in moduli separati - vedi sezione "Code Architecture & Modular Structure" sotto.

---

#### **Task 4.2: Generic Gate Tracking Refactor** ✅ **COMPLETED** (2025-01-01 → 2025-01-03)
**Problema**: Gate tracking hardcoded per Consist 11 only.

**Goal**: Config-driven multi-consist support
- Replace hardcoded variables con `self.consist_data` dict
- Load `tracking_assignments` from config.json
- Generic method `_update_gate_timing(consist_id, lead_pos, rear_pos)`
- Loop over all configured consists dynamically

**Benefits**:
- ✅ Add Consist 10/12/13+ without code changes
- ✅ Change gate assignments via JSON (no recompile)
- ✅ Single method for ALL consists (no duplication)
- ✅ Supports both symmetric (C11) and asymmetric (C10) gate timing modes

**Status**: ✅ **COMPLETED**
- ✅ `consist_data` dict replaces all hardcoded variables
- ✅ Generic `_update_gate_timing()` works for ANY consist
- ✅ Multi-consist support via config.json
- ✅ See `docs/CONSIST_TRACKING.md` for details

**Implementation**: 7 steps completed
1. ✅ Load `tracking_assignments` from config
2. ✅ Replace hardcoded variables with `consist_data` dict
3. ✅ Refactor `_update_gate_timing()` to generic
4. ✅ Refactor `_calculate_delta_t()` per-consist
5. ✅ Update `update()` loop for all consists
6. ✅ Update WebSocket broadcast format
7. ✅ Update frontend to parse multi-consist data

---

#### **Phase 4B: Virtual Consist Mode** ✅ **COMPLETED** (implemented & tested 2025-12-31 → 2025-01-03)
**Software-level consist control con automatic CV19 management**

**Obiettivo**: Controllare locomotive in consist SEPARATAMENTE a livello software senza dover usare CV adjustment manuale, permettendo speed compensation real-time tramite Δt feedback da Phase 4.

**Status**: ✅ **FULLY IMPLEMENTED & TESTED**
- ✅ CV19 toggle automatico (DCC ↔ Virtual Mode)
- ✅ Speed compensation con Δt feedback da gate timing
- ✅ UI toggle in ConsistController con status indicators
- ✅ Persist state in consist_state.json
- ✅ Auto-compensation toggle (enable/disable in Virtual Mode)
- ✅ WebSocket messages: `toggle_virtual_mode`, `toggle_auto_compensation`
- ✅ Backend implementation in z21_manager.py

**⚠️ INSIGHT CRITICO (2025-12-30 sera)**:
- **CV19 WRITE in operations mode funziona su TUTTE le locomotive** (confermato 2025-12-29)
- **NO programming track necessaria** - JMRI usa operations mode per consist management
- User conferma: "Io non metto mai nessuna loco in programming track, apro il consist tool, aggiungo o tolgo loco, lo chiudo ed i rispettivi CV 19 delle loco sono settati"
- **Solo CV READ problematico** su Hornby TXS (ma non necessario per Virtual Consist)

**✅ TRACKING MODE-INDEPENDENT** (confermato 2025-12-31):
- **Tracking Δt funziona SEMPRE**: indipendente da DCC/Virtual Mode
- **DCC Mode** (CV19 = consist_address):
  - ✅ Δt monitoring attivo (gate timing detection continua)
  - ❌ Speed compensation disabilitato (loco rispondono solo a consist address)
  - 📊 UI label: **"Speed compensation disabled"** (icona `fa-gauge-high` grigia)
- **Virtual Mode** (CV19 = 0):
  - ✅ Δt monitoring attivo (gate timing detection continua)
  - ✅ Speed compensation abilitato (loco rispondono a address individuali)
  - 🎚️ UI label: **"Speed compensation enabled"** (icona `fa-gauge-high` verde/amber)
- **Test eseguiti**: Toggle DCC↔Virtual, CV19 verificato (valori 11↔0), tracking sempre attivo

**Strategia Virtual Consist**:
1. **Toggle Virtual Mode** (click pulsante in UI):
   - App scrive automaticamente `CV19 = 0` su ENTRAMBE le locomotive (operations mode)
   - Libera locomotive dal consist DCC
   - Locomotive ora rispondono ai loro address nativi (1, 5, 7, 8)
   - App controlla velocità separatamente ma in modo coordinato

2. **Toggle DCC Mode** (click pulsante in UI):
   - App scrive automaticamente `CV19 = consist_address` (10 o 11) su entrambe le locomotive
   - Restore consist DCC standard
   - Locomotive tornano a rispondere solo all'address del consist

**Vantaggi Virtual Mode**:
- ✅ **Zero intervento manuale**: utente clicca toggle, app fa tutto automaticamente
- ✅ **Speed compensation real-time**: usa Δt da gate timing per aggiustare velocità
- ✅ **Transparente per utente**: vede UN solo slider, app gestisce dual control
- ✅ **Reversibile istantaneamente**: toggle back a DCC mode in 1 click
- ✅ **No programming track**: tutto via operations mode (locomotive in movimento)

**UI Design**:
```
┌─────────────────────────────────────────┐
│ Header Right:  ⚡ 📶 🖥️ 🌙  [⚙️ Consists] │ ← New button
└─────────────────────────────────────────┘

Click [⚙️ Consists] → Modal overlay:

┌─────────────────────────────────────────┐
│ ⚙️ Consist Manager               [×]    │
├─────────────────────────────────────────┤
│ Consist 10 - Gr.675 + D645              │
│   Lead: Loco 1 (Gr.675 017)             │
│   Rear: Loco 5 (D645 014)               │
│   Mode: [DCC Consist ▼]                 │
│         [Virtual Consist]  ← Toggle     │
│   [Edit] [Delete]                       │
├─────────────────────────────────────────┤
│ Consist 11 - E656 + E444                │
│   Lead: Loco 7 (E656 239)               │
│   Rear: Loco 8 (E444 056)               │
│   Mode: [Virtual Consist ▼]             │
│         [DCC Consist]  ← Toggle         │
│   🎚️ Speed compensation enabled          │
│   Current Δt: +0.234s 🟢 SYNCED         │
│   [Edit] [Delete]                       │
├─────────────────────────────────────────┤
│ [+ Create New Consist]                  │
└─────────────────────────────────────────┘
```

**Backend Implementation** (`backend/consist_manager.py`):
```python
class ConsistManager:
    """Manage virtual consists with automatic CV19 handling"""

    def __init__(self, z21_instance, roster_path):
        self.z21 = z21_instance
        self.consists = self.load_consists(roster_path)
        self.consist_config_path = "consist_config.json"

    def enable_virtual_mode(self, consist_address):
        """
        Enable Virtual Consist Mode
        - Write CV19=0 to both locomotives (operations mode)
        - Update consist config to mode='virtual'
        - Return success status
        """
        consist = self.consists[consist_address]
        lead_addr = consist['lead_address']
        rear_addr = consist['rear_address']

        # Write CV19=0 to free locomotives from consist
        success_lead = self.z21.write_cv_ops_mode(lead_addr, 19, 0)
        success_rear = self.z21.write_cv_ops_mode(rear_addr, 19, 0)

        if success_lead and success_rear:
            consist['mode'] = 'virtual'
            self.save_config()
            return True
        return False

    def disable_virtual_mode(self, consist_address):
        """
        Disable Virtual Mode → restore DCC consist
        - Write CV19=consist_address to both locomotives
        - Update consist config to mode='dcc'
        """
        consist = self.consists[consist_address]
        lead_addr = consist['lead_address']
        rear_addr = consist['rear_address']

        # Restore CV19 to consist address
        success_lead = self.z21.write_cv_ops_mode(lead_addr, 19, consist_address)
        success_rear = self.z21.write_cv_ops_mode(rear_addr, 19, consist_address)

        if success_lead and success_rear:
            consist['mode'] = 'dcc'
            self.save_config()
            return True
        return False

    def set_virtual_speed(self, consist_address, target_speed, delta_t=0):
        """
        Set speed for virtual consist with Δt compensation
        - target_speed: user slider value (0-126)
        - delta_t: gate timing feedback (from Phase 4)
        """
        consist = self.consists[consist_address]

        if consist['mode'] != 'virtual':
            # DCC mode: send to consist address
            self.z21.set_loco_speed(consist_address, target_speed)
        else:
            # Virtual mode: control separately with compensation
            lead_speed = target_speed
            rear_speed = target_speed

            # Δt compensation (simple proportional for MVP)
            if abs(delta_t) > 0.1:  # Only compensate if |Δt| > 100ms
                # Δt > 0: lead passing first (too fast) → slow down lead
                # Δt < 0: rear passing first (too fast) → slow down rear
                compensation = int(delta_t * 5)  # 5 speed steps per second Δt

                if delta_t > 0:
                    lead_speed = max(0, lead_speed - compensation)
                else:
                    rear_speed = max(0, rear_speed + compensation)

            # Send individual commands
            self.z21.set_loco_speed(consist['lead_address'], lead_speed)
            self.z21.set_loco_speed(consist['rear_address'], rear_speed)
```

**Frontend Integration** (`web/src/App.jsx`):
- Dropdown selection aggiornato: mostra TUTTI i consist (sia DCC che Virtual)
- Slider `onChange`: chiama endpoint che usa `ConsistManager.set_virtual_speed()`
- Transparent per utente: vede UN slider, app gestisce dual control se Virtual mode

**Workflow Utente** (esempio Consist 11):
1. User apre app → Consist 11 attualmente in DCC mode (CV19=11)
2. User clicca [⚙️ Consists] → modal si apre
3. User vede "Consist 11 - Mode: [DCC Consist ▼]"
4. User clicca dropdown → seleziona "Virtual Consist"
5. **App automaticamente**:
   - Scrive CV19=0 su loco 7 (operations mode, loco in movimento)
   - Scrive CV19=0 su loco 8 (operations mode, loco in movimento)
   - Aggiorna `consist_config.json` con mode='virtual'
   - UI mostra "Mode: [Virtual Consist ▼]" + "Speed compensation active"
6. User muove slider velocità → app controlla loco 7 e 8 separatamente
7. Gate timing Δt feedback → app aggiusta automaticamente velocità relativa
8. User vede risultato: consist sincronizzato, Δt → 0
9. **Per tornare a DCC mode**: User clicca dropdown → "DCC Consist"
   - App scrive CV19=11 su entrambe (operations mode)
   - Tornano a consist standard

**Data Storage** (`consist_config.json`):
```json
{
  "10": {
    "name": "Gr.675 + D645",
    "lead_address": 1,
    "rear_address": 5,
    "mode": "dcc",
    "delta_t_threshold": 0.5
  },
  "11": {
    "name": "E656 + E444",
    "lead_address": 7,
    "rear_address": 8,
    "mode": "virtual",
    "delta_t_threshold": 0.5,
    "compensation_factor": 5
  }
}
```

**WebSocket API Updates**:
- New message types:
  - `enable_virtual_mode`: { consist_address }
  - `disable_virtual_mode`: { consist_address }
  - `virtual_mode_status`: { consist_address, mode, success }
  - `delta_t_update`: { consist_address, delta_t, status } (from YOLO tracking)

**Implementation Tasks**:
- [ ] Create `backend/consist_manager.py` with `ConsistManager` class
- [ ] Initialize `consist_config.json` from JMRI roster (first run)
- [ ] Add CV19 write/restore methods (use existing `z21.write_cv_ops_mode()`)
- [ ] Implement `set_virtual_speed()` with Δt compensation
- [ ] Add WebSocket endpoints for consist CRUD + mode toggle
- [ ] Frontend: ⚙️ Consists button in header
- [ ] Frontend: Modal overlay for consist management
- [ ] Frontend: Consist list with mode toggle dropdown
- [ ] Frontend: Integration with existing controller dropdown
- [ ] Test CV19 write cycle on one consist (verify operations mode reliability)
- [ ] Test speed compensation with real Δt feedback from Phase 4

**Testing Plan**:
1. **CV19 Write Verification**:
   - Enable Virtual mode → verify CV19=0 (via JMRI DecoderPro or Bluetooth app)
   - Disable Virtual mode → verify CV19=consist_address restored
2. **Speed Control**:
   - Virtual mode: verify locomotives respond to individual addresses
   - DCC mode: verify locomotives respond only to consist address
3. **Δt Compensation**:
   - Create artificial Δt (manual speed mismatch)
   - Verify app compensates automatically
   - Verify Δt → 0 over time

**Success Criteria**:
- ✅ Toggle Virtual/DCC mode in < 2 seconds (2x CV19 writes)
- ✅ Speed compensation reduces |Δt| by 50% within 30 seconds
- ✅ Zero user intervention needed (fully automatic CV19 management)
- ✅ Transparent UX (user sees single slider, doesn't know about dual control)

**Next Phase Integration**:
- Phase 8 (Auto CV Adjust) può coesistere con Virtual Consist Mode
- Virtual mode = real-time compensation (session-based, NO CV write)
- Auto CV Adjust = permanent CV changes (speed table tuning)
- User può usare Virtual mode per quick fixes, poi Auto CV Adjust per permanent tuning

#### **Phase 7: Track Occupancy Map** ⏸️ **POSTPONED** (implementation plan complete, execution deferred)
**Real-time locomotive positions on SVG track layout**

**Status**: Piano implementazione completo, feature posticipata (video feed debug overlay già sufficiente)

**Obiettivo**: Visualizzazione real-time posizioni locomotive su mappa SVG 2D del plastico con trasformazione prospettica camera → piano ortogonale.

**Stack pianificato**:
- React components: `TrackMapView`, `TrackMapSVG`, `LocomotiveMarker`
- Perspective transform: Camera 1280x720 oblique → SVG 600x1200 orthogonal (6px/cm)
- Tunnel interpolation: Smooth transition durante galleria C10 (~5s blind spot)
- WebSocket sync: Real-time YOLO detection → transformed coordinates

**Features pianificate**:
- ✓ Locomotive markers (cerchi colorati con direction arrows)
- ✓ Info overlays (ID, nome, speed, direction, confidence)
- ✓ Gate overlays (transformed coordinates da config.json)
- ✓ Track paths ridisegnati da layout foto

**Motivo postpone**:
- Video feed con debug overlay (B key) già fornisce visualizzazione sufficiente
- Bounding boxes + pallini + confidence labels coprono casi d'uso principali
- Complessità implementazione (12-18h) vs beneficio incrementale non giustificato
- Può essere ripreso in futuro se necessario (piano completo già disponibile)

**Documentazione completa**: `docs/TRACK_MAP_IMPLEMENTATION.md` (workspace notes)

---

#### **Phase 8: Auto CV Adjust** (very low priority)
**⚠️ VERY LOW PRIORITY - Virtual Mode già fornisce compensazione real-time**
**Basato su co-presence timing Δt da Phase 4**

**⚙️ Reference Loco Strategy**:
- **Consist 11**: Reference = loco 8 (ESU stabile), Adjust = loco 7 (Hornby instabile)
- **Consist 10**: Reference = da determinare (probabilmente D645 014 ESU)
- **Mai toccare CV della reference loco** (curva perfetta da preservare)

- [ ] **CV adjustment calculator** basato su co-presence timing Δt
  - **Consist 11 - Adjustment loco 7 (lead)**:
    - **Δt > 0** (loco 7 passa prima) → loco 7 troppo veloce:
      - **Rallenta loco 7**: aumenta CV2 (Vstart) o CV5 (Vhigh) o step speed table
      - Mai toccare loco 8 (reference stabile)
    - **Δt < 0** (loco 8 passa prima) → loco 7 troppo lenta:
      - **Accelera loco 7**: diminuisci CV2 o CV5 o step speed table
      - Mai toccare loco 8 (reference stabile)
    - **Obiettivo**: Δt → 0 (sincronizzazione perfetta)
  - **Consist 10 - Gap drift**:
    - Gap tempo lead→rear si riduce → tamponamento risk
    - Adjustment sulla loco meno stabile (da determinare test)
  - **Soglie**: |Δt| > 0.5s warning, |Δt| > 1.0s critical, |Δt| > 2.0s emergency
- [ ] **Safety checks** (max ±5 adjust/session, cooldown 30sec, confirmation UI)
- [ ] **OPS mode write automation** con abort immediato su errore
  - Loco 7 (Hornby TXS): ✅ CV write OK
  - Loco 8 (ESU): ✅ CV write OK (ma non lo toccheremo mai)
- [ ] **History log UI** con severity levels (CRITICAL/WARNING/INFO)
- [ ] **Emergency stop integration** quando |Δt| > 2.0s (intervento automatico)

#### **Phase 6: Software Sync Mode** ✅ **COMPLETED** (implemented as Phase 4B Virtual Mode)
**Real-time dual speed control con timing sync algorithm**

**Status**: ✅ Questa fase è già **COMPLETAMENTE IMPLEMENTATA** come parte di Phase 4B (Virtual Consist Mode)

**Cosa include Virtual Mode (Phase 4B)**:
- ✅ **Dual speed control real-time** - Loco reference + adjust ricevono speed separate (z21_manager.py lines 175-338)
- ✅ **Timing sync algorithm** - Compensation basata su Δt con soglie CRITICAL/WARNING/SYNCED
- ✅ **Incremental compensation** - `speed_actual_adjust` aggiornato in tempo reale
- ✅ **Auto-compensation toggle** - Enable/disable senza riavviare
- ✅ **CV19 management** - Toggle DCC ↔ Virtual con un click (scrive CV19 solo per mode switch)

**Differenza teorica Phase 6**:
- Descrizione originale: "non scrive CV" (implicava dual control SENZA liberare consist)
- **Problema**: Locomotive in consist DCC (CV19=10/11) ignorano comandi ai loro address individuali
- **Soluzione implementata**: Virtual Mode scrive CV19=0 UNA VOLTA per liberare, POI fa dual control senza ulteriori write

**Conclusione**: Phase 6 è un duplicato di Phase 4B. Il "Software Sync Mode" descritto in Phase 6 corrisponde esattamente al comportamento di Virtual Consist Mode già implementato e testato.

---

## Code Architecture & Modular Structure

**Status**: ✅ **Refactoring Completato** (2026-01-06) - Eliminata duplicazione codice tra daemon e script standalone

### Modular Design Overview

Il sistema tracking è stato refactored per eliminare ~933 righe di codice duplicato (-37%) e creare una architettura modulare condivisa.

**Problema originale**:
- `backend/tracking_daemon.py` (headless WebSocket daemon): 1049 righe
- `scripts/track_consist_yolo.py` (GUI testing script): 1287 righe
- **933 righe duplicate** tra i due file (YOLO detection logic, gate timing, RTSP handling)

**Soluzione**: Moduli condivisi in `backend/tracking/`

### New Module Structure

```
backend/tracking/
├── __init__.py              # Module exports (12 lines)
├── yolo_tracker.py          # Core YOLO + gate timing logic (551 lines)
└── rtsp_handler.py          # RTSP stream management (110 lines)
```

#### `backend/tracking/yolo_tracker.py` (551 lines)

**Core tracking logic centralizzato**:
- YOLO model loading and inference
- Multi-consist detection and tracking
- Gate crossing detection (dual-gate timing)
- Δt calculation with cross-validation
- Position update handling (single/dual loco detection)
- Consist state management (`consist_data` dict)
- Debug overlay rendering (optional)

**Key class**: `YOLOTracker`

```python
class YOLOTracker:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.consist_data = {}  # Per-consist state
        self.gates = {}         # Gate definitions from config
        # ... initialization

    def update(self, frame):
        """Process frame, detect locomotives, update gate timing"""
        results = self.model(frame, ...)
        # ... detection logic
        return tracking_data

    def _update_gate_timing(self, consist_id, lead_pos, rear_pos):
        """Generic gate timing for ANY consist (config-driven)"""
        # ... dual-gate co-presence timing

    def _calculate_delta_t(self, consist_id):
        """Calculate Δt with cross-gate validation"""
        # ... Δt calculation logic
```

**Benefits**:
- ✅ Single source of truth for YOLO detection
- ✅ Config-driven multi-consist support
- ✅ Reusable across daemon + standalone script
- ✅ Easier to test and maintain

#### `backend/tracking/rtsp_handler.py` (110 lines)

**RTSP stream management utilities**:
- Camera config loading (`camera_config.json`)
- Optimal VideoCapture setup (minimal buffering)
- Reconnection logic for unstable streams
- Stream description for debugging

**Key functions**:

```python
def load_camera_config():
    """Load RTSP URL from camera_config.json"""
    # ... config loading

def setup_rtsp_stream(rtsp_url, description="RTSP stream"):
    """Setup cv2.VideoCapture with optimal settings"""
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize lag
    # ... additional setup
    return cap

def reconnect_rtsp_stream(cap, rtsp_url, description):
    """Attempt to reconnect lost RTSP stream"""
    # ... reconnection logic
```

**Benefits**:
- ✅ Centralized RTSP configuration
- ✅ Consistent buffering settings across all scripts
- ✅ Reusable reconnection logic

#### `backend/tracking/__init__.py` (12 lines)

**Module exports**:

```python
from .yolo_tracker import YOLOTracker
from .rtsp_handler import (
    setup_rtsp_stream,
    load_camera_config,
    reconnect_rtsp_stream
)

__all__ = [
    'YOLOTracker',
    'setup_rtsp_stream',
    'load_camera_config',
    'reconnect_rtsp_stream'
]
```

### Refactored Files

#### `backend/tracking_daemon.py` (476 lines, -55% reduction)

**Before**: 1049 lines (included full YOLO + gate logic)
**After**: 476 lines (imports from `backend/tracking/`)

**Now focuses on**:
- WebSocket communication (backend sync)
- FPS mode management (active/idle)
- Δt broadcasting to frontend
- Frame queue producer (for video feed)
- Daemon lifecycle management

**Imports shared logic**:
```python
from tracking.yolo_tracker import YOLOTracker
from tracking.rtsp_handler import setup_rtsp_stream, load_camera_config

class TrackingDaemon:
    def __init__(self):
        self.tracker = YOLOTracker(str(MODEL_PATH))
        # ... daemon-specific setup

    async def run(self):
        self.cap = setup_rtsp_stream(RTSP_URL)
        # ... daemon loop uses tracker.update(frame)
```

#### `scripts/track_consist_yolo.py` (1063 lines, -17% reduction)

**Before**: 1287 lines (included full YOLO + gate logic)
**After**: 1063 lines (imports from `backend/tracking/`)

**Now focuses on**:
- OpenCV GUI (interactive visualization)
- User input handling (keyboard controls)
- Debug panels rendering
- Gate editing mode (drag, resize, rotate)
- Session statistics

**Imports shared logic**:
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from tracking.yolo_tracker import YOLOTracker
from tracking.rtsp_handler import setup_rtsp_stream, load_camera_config

def main():
    tracker = YOLOTracker(str(MODEL_PATH))
    cap = setup_rtsp_stream(RTSP_URL)
    # ... GUI loop uses tracker.update(frame)
```

### Refactoring Benefits

**Code Reduction**:
- `tracking_daemon.py`: 1049 → 476 lines (-573 lines, -55%)
- `track_consist_yolo.py`: 1287 → 1063 lines (-224 lines, -17%)
- **Total net reduction**: ~933 lines (-37% duplication eliminated)

**Maintainability**:
- ✅ YOLO detection logic: 1 place to update (not 2)
- ✅ Gate timing algorithm: 1 implementation (not 2)
- ✅ Bug fixes propagate automatically to both daemon + script
- ✅ Config-driven design: add new consists via JSON (no code changes)

**Testing**:
- ✅ Standalone script still works (GUI testing)
- ✅ Daemon still works (production headless mode)
- ✅ Both share exact same detection logic (no divergence)

**Fixes Applied During Refactoring**:
- ✅ Position updates handle single loco detection correctly
- ✅ Bounding boxes included in detections for debug mode
- ✅ Consist names added to consist_config
- ✅ Gate colors propagated from config.json
- ✅ Co-visibility panel removed (redundant)
- ✅ Debug overlay moved before early return (always visible with D key)
- ✅ All info panels resized to uniform 430px width
- ✅ Z21 offline error handling (backend startup graceful)

### Usage Examples

**Headless daemon** (production):
```bash
cd backend
python tracking_daemon.py
# Uses YOLOTracker from backend/tracking/
# Broadcasts Δt via WebSocket to FastAPI
```

**Standalone GUI script** (testing):
```bash
cd scripts
python track_consist_yolo.py
# Uses YOLOTracker from backend/tracking/
# Shows OpenCV window with debug overlays
```

**Both scripts**:
- Load same YOLO model (`scripts/models/best.pt`)
- Use same gate definitions (`config.json`)
- Run same detection algorithm (`YOLOTracker.update()`)
- Calculate same Δt values (cross-gate validation)

---

### Esperimenti Phase 3 - Motion Detection (ARCHIVIATO)

**Status**: ❌ Approccio motion detection puro **abbandonato** - insufficiente per tracking affidabile

**Conclusione**: Background subtraction (MOG2) troppo sensibile a illuminazione/ombre, impossibile distinguere lead/rear senza ML.

**Decisione**: Adottato **YOLO custom training** (object detection ML) → ✅ **funzionante** (vedi sezione sotto)

**Dettagli completi**: Vedi `docs/CHANGELOG_ARCHIVE.md` (4 approcci testati, problemi identificati, conclusioni)

### Nuovo Approccio: YOLO Object Detection (decisione 2025-12-29)

**Decisione**: Abbandonare motion detection puro, adottare **YOLO custom training** per tracking robusto.

#### Cos'è YOLO

**YOLO** = **You Only Look Once** - algoritmo di object detection basato su deep learning.

**Differenza chiave**:
- **Motion detection** (provato): "C'è qualcosa che si muove?" → non sa COSA
- **YOLO**: "Qui c'è una LOCOMOTIVA E656, qui una E444, qui una CASA" → riconosce COSA sono gli oggetti

**Output YOLO**:
```python
📦 Loco E656_239 (95% confidence) - x:450, y:230, w:120, h:80
📦 Loco E444_056 (92% confidence) - x:820, y:180, w:115, h:75
🏠 Casa (85% confidence) - x:100, y:500 ← ignorabile
```

**Vantaggi per il progetto**:
- ✅ Riconosce SOLO le locomotive specifiche, ignora case/edifici/ombre
- ✅ Distingue lead da rear (due locomotive diverse addestrate)
- ✅ Funziona anche ferme (non serve movimento)
- ✅ Robusto a illuminazione variabile
- ✅ Fornisce confidence score (% sicurezza rilevamento)

**Svantaggi**:
- ❌ Richiede training custom (200-300 foto annotate)
- ❌ Setup più complesso rispetto a motion detection
- ⚠️ Training richiede GPU (ma può usare Google Colab gratis)

#### Processo Completo (Timeline: 1-2 giorni)

**Phase 3A: Dataset Creation** (1-2 ore)

ℹ️ **Workflow completo disponibile in `scripts/utils/README.md`** - Include tutti gli step e comandi pronti all'uso

1. **Registrazione video** (10-15 min):
   ```bash
   cd scripts/utils
   python 1_record_video.py [output_filename.mp4]
   # Registra mentre consist 11 fa 5-10 giri completi del tracciato
   # Cattura: tutte le angolazioni, curva, rettilineo, galleria
   # Controls: R=start/stop recording, Q=quit, SPACE=pause/resume
   ```

2. **Estrazione frames** (automatico - 5 min):
   ```bash
   cd scripts/utils
   python 2_extract_frames.py consist11_training.mp4 --interval 10
   # Estrae 1 frame ogni 10 (da 5min video @ 15fps = ~450 frames → 45 foto)
   # --interval 5 per più varietà (~90 foto)
   # Output: data/frames/
   ```

3. **Annotazione manuale** (20-40 min):
   - Tool: **LabelImg** (più semplice, raccomandato)
   - Installazione: `pip install labelImg`
   - Workflow:
     1. Apri foto
     2. Click "Create RectBox"
     3. **Disegna rettangolo** (bounding box) intorno a locomotiva con mouse
     4. Assegna classe: "E656_lead" o "E444_rear"
     5. Salva (genera XML con coordinate)
     6. Next → ripeti (5-10 secondi per foto)

   **Formato output** (YOLO):
   ```
   # image001.txt
   0 0.5234 0.3456 0.1234 0.0876
   │   │      │      │      └─ Altezza (% dell'immagine)
   │   │      │      └─ Larghezza (% dell'immagine)
   │   │      └─ Centro Y (% dall'alto)
   │   └─ Centro X (% da sinistra)
   └─ Classe ID (0=E656_lead, 1=E444_rear)
   ```

   **Alternative tools**:
   - **Roboflow** (roboflow.com) - online, annotazione assistita automatica
   - **CVAT** - più avanzato, supporta video diretto (no estrazione frames)

**Phase 3B: Training YOLO** (1-2 ore su Google Colab)

**Quick Start**: Usa lo script completo `scripts/utils/3_train_yolo_colab.py` (copy-paste in Colab)

1. **Setup ambiente**:
   ```python
   # Google Colab (GPU gratis)
   !pip install ultralytics

   from ultralytics import YOLO
   ```

2. **Configurazione dataset** (`data.yaml`):
   ```yaml
   train: dataset/images/train
   val: dataset/images/val

   nc: 2  # Numero classi
   names: ['E656_lead', 'E444_rear']
   ```

3. **Training**:
   ```python
   # YOLOv8 nano (veloce, leggero)
   model = YOLO('yolov8n.pt')

   # Train per 50 epochs (~1 ora su Colab GPU)
   results = model.train(
       data='data.yaml',
       epochs=50,
       imgsz=640,
       batch=16
   )

   # Download model.pt (file finale, ~6MB)
   ```

**Phase 3C: Integrazione nel progetto** (1-2 ore)

1. **Script tracking aggiornato** (`track_consist_yolo.py`):
   ```python
   from ultralytics import YOLO
   import cv2

   # Load trained model
   model = YOLO('locomotiva_model.pt')

   # RTSP camera
   cap = cv2.VideoCapture(rtsp_url)

   while True:
       ret, frame = cap.read()
       if not ret: break

       # YOLO detection
       results = model(frame, conf=0.6)  # Confidence threshold 60%

       # Parse detections
       for box in results[0].boxes:
           x, y, w, h = box.xywh[0]
           class_id = int(box.cls[0])
           confidence = float(box.conf[0])

           if class_id == 0:  # E656_lead
               lead_pos = (int(x), int(y))
               print(f"Lead detected at {lead_pos} ({confidence:.2%})")
           elif class_id == 1:  # E444_rear
               rear_pos = (int(x), int(y))
               print(f"Rear detected at {rear_pos} ({confidence:.2%})")

       # Calculate distance, draw markers, etc.
   ```

2. **Vantaggi implementazione**:
   - Nessun background subtraction (elimina flash periodici)
   - Nessun pattern analysis (loco riconosciute direttamente)
   - Nessun calcolo direzione necessario (YOLO trova la loco, non il centro)
   - Robusto: funziona anche su tutto il tracciato ovale

**Phase 3D: Testing & Refinement** (1-2 ore)

- Test su tracciato completo (tutte le posizioni)
- Verifica confidence scores (target: >80%)
- Se detection instabile: aggiungere più foto annotate + re-training

#### Requisiti

**Software**:
- Python 3.8+
- ultralytics (YOLOv8)
- OpenCV
- labelImg (annotazione)

**Hardware**:
- ✅ Tapo IP camera (già disponibile)
- ✅ Mac locale per inference (CPU ok, YOLO nano veloce)
- ☁️ Google Colab per training (GPU gratis)

**Dataset minimo**:
- 50-100 foto annotate (minimo assoluto)
- 200-300 foto annotate (raccomandato per robustezza)
- Nel tuo caso: 100-150 foto sufficienti (camera fissa, illuminazione controllata)

#### Timeline Realistica

| Phase | Attività | Tempo | Status |
|-------|----------|-------|--------|
| 3A | Dataset creation (video + frames + annotazione) | 1-2 ore | ✅ COMPLETATO |
| 3B | Training YOLO su Colab | 1-2 ore | ✅ COMPLETATO |
| 3C | Integrazione script | 1-2 ore | ✅ COMPLETATO |
| 3D | Testing & refinement | 1-2 ore | ✅ COMPLETATO |
| **TOTALE** | **Fine-to-end** | **4-8 ore** | ✅ **COMPLETATO** |

**✅ Completato in 1 giorno (2025-12-29/30)** - Model v3 funzionante, tutte e 4 locomotive detectate! 🎯

#### YOLO Model Versions History

**Model v3** (2025-12-29) - Initial training
- **Dataset**: Roboflow v3 - 137 images
- **Training**: YOLOv8 nano, 50 epochs, 4 minutes GPU T4
- **Result**: mAP50 = 80.7%
- **Detection**: Confidence 0.60-0.92 (all 4 locomotives)
- **Status**: ✅ Working, deployed in production

**Model v4** (2025-12-30) - Rectangular optimization for GPU
- **Dataset**: Roboflow v4 - "Fit within 1280x1280" (preserves 16:9 aspect ratio)
- **Training**: YOLOv8 nano, rectangular mode (640x1152), 50 epochs
- **Result**: mAP50 = 0.919
- **Rationale**: Optimized for GPU deployment, zero padding waste, matches camera native 16:9
- **Deployment**: Reserved for future PC GPU production deployment
- **File**: `scripts/models/BiancAlice_v4.pt` (saved, not active)

**Model v5** (2025-01-05) - Square optimization for CPU
- **Dataset**: Roboflow v5 - "Stretch to 640x640" (square with distortion)
- **Training**: YOLOv8 nano, square mode (640x640), 50 epochs, batch 16, patience 10
- **Result**: mAP50 = **0.931** (best standard model)
- **Rationale**: Faster inference on Mac CPU, simpler processing, best mAP achieved
- **Deployment**: Currently active as `scripts/models/best.pt`
- **Inference size**: Configurable via `config.json` → `tracking.yolo_imgsz: 640`
- **Training time**: 4 minutes on Google Colab GPU T4
- **File**: `scripts/models/best.pt` (standard axis-aligned bounding boxes)

**Model v6 OBB** (2025-01-10) - Oriented Bounding Boxes
- **Dataset**: Roboflow v5 - same as v5, auto-converted to OBB format
- **Training**: YOLOv8n-OBB, square mode (640x640), 50 epochs
- **Result**: mAP50 = **0.917** (91.7%, slightly lower than v5)
- **Rationale**: Rotated bounding boxes follow locomotive orientation → better overlap handling
- **Initial testing results** (production PC + GPU, 2025-01-10):
  - ✅ **Overlap handling**: Perfect - both locos visible when passing close (bbox don't overlap)
  - ✅ **Bbox orientation**: Rotated polygons follow locomotive angle
  - ❌ **Distant detection**: Confidence drops <0.4 on distant locos (loco 7 especially)
    - Required `yolo_confidence: 0.1` to detect → false positives (wagons, double bbox)
  - **Initial decision**: NOT DEPLOYED (suboptimal params)
- **Refined testing results** (2025-01-11):
  - ✅ **Overlap handling**: Perfect (bbox ruotati geometricamente ottimali)
  - ✅ **Distant detection**: Confidence 0.3 bilancia detection vs false positives
  - ✅ **IoU optimization**: 0.6 sufficiente (OBB riduce overlap geometrico)
  - **Key insight**: OBB richiede tuning diverso (confidence più alto, IoU più basso)
- **Decision**: ✅ **DEPLOYED IN PRODUCTION** (dopo parameter tuning)
- **File**: `scripts/models/best_obb.pt` - **ACTIVE** ✅

**Model Selection (Auto-Switching)**:
- **Implementation**: `yolo_tracker.py` auto-selects model based on `config.json` → `tracking.yolo_obb` flag
  - `yolo_obb: false` → loads `best.pt` (standard axis-aligned)
  - `yolo_obb: true` → loads `best_obb.pt` (Oriented Bounding Boxes) ✅ **ACTIVE**
- **Log message**: Always visible at startup (not debug-gated)
- **No manual renaming needed**: Switch model by changing config flag + restart backend

**Production Testing Comparison** (2025-01-10 → 2025-01-11):
| Model | Distant Detection | Overlap Handling | False Positives | Confidence | IoU | Status |
|-------|------------------|------------------|-----------------|------------|-----|--------|
| **v5 Standard** (initial) | ✅ Excellent (0.4+ distant) | ⚠️ Good (NMS <95% overlap) | ✅ Low (conf 0.2) | 0.2 | 0.95 | Tested |
| **v6 OBB** (initial) | ❌ Poor (<0.4 distant) | ✅ Perfect (rotated bbox) | ⚠️ High (conf 0.1 req) | 0.1 | 0.85 | Rejected |
| **v6 OBB** (tuned) | ✅ Excellent | ✅ Perfect | ✅ Low | 0.3 | 0.6 | ✅ **ACTIVE** |

**Final Configuration** (production 2025-01-11):
```json
{
  "tracking": {
    "yolo_confidence": 0.3,  // Higher than standard (OBB requires different tuning)
    "yolo_iou": 0.6,         // Lower than standard (OBB reduces geometric overlap)
    "yolo_obb": true         // OBB model selected
  }
}
```

**Key Insights**:
- **OBB requires different tuning**: Confidence higher (0.3 vs 0.2), IoU lower (0.6 vs 0.95)
- **Geometry matters**: Rotated bbox reduce overlap → lower IoU threshold works better
- **False positives solvable**: Confidence 0.3 is sweet spot for OBB (0.2 too low, 0.1 way too low)
- **Production testing iterative**: Initial OBB tests had suboptimal params, refined tuning essential
- **Trade-off eliminated**: OBB with proper tuning has no downsides vs standard model

---

### TensorRT GPU Optimization (2025-01-11)

**Goal**: Reduce bbox lag from 2-3s to <0.5s via GPU-accelerated inference

**Implementation**:
- Export YOLO model to TensorRT `.engine` format (FP16 half-precision)
- Script: `scripts/utils/export_tensorrt.py` (auto-detects standard vs OBB from config)
- Auto-detection fallback: `.engine` → `.onnx` → `.pt`
- Priority: Maximum speed with zero accuracy loss

**Critical Bug Discovered & Fixed**:
- **Problem**: ONNX/TensorRT exports showed zero detection (no bboxes, no console output)
- **Root cause**: Export process strips model metadata including `task` parameter
  - YOLO assumed `task='detect'` instead of `task='obb'`
  - OBB model treated as standard detection → incompatible output format
- **Solution**: Explicitly specify `task='obb'` when loading OBB models
  ```python
  # yolo_tracker.py
  if yolo_obb:
      self.model = YOLO(model_path, task='obb')  # Explicit for ONNX/TensorRT OBB
  else:
      self.model = YOLO(model_path)              # Standard detection
  ```
- **Commits**: `1012ccb` (ONNX fallback), `2d17969` (task='obb' fix)

**Production Results** (PC Windows RTX 2060):
| Format | Speed | Bbox Lag | File Size | Status |
|--------|-------|----------|-----------|--------|
| PyTorch `.pt` | ~30ms/frame | 2-3s | 6.6 MB | Backup |
| ONNX `.onnx` | ~15-20ms/frame (1.5-2x) | <1s | 11.9 MB | Intermediate |
| TensorRT `.engine` | **~6-15ms/frame (2-5x)** | **<0.5s** | 13.7 MB | ✅ **ACTIVE** |

**Performance Impact**:
- ✅ **Bbox lag**: Eliminated (2-3s → <0.5s)
- ✅ **Gate timing**: Real-time accurate (<100ms delay)
- ✅ **Video feed**: Smooth, zero frame drops
- ✅ **Detection**: Perfect with rotated bboxes (all 4 locos)
- ✅ **Fallback**: Automatic (ONNX intermediate if TensorRT fails)

**Export Time**: ~2 minutes one-time (GPU-specific optimization)

**Hardware Requirements**:
- NVIDIA GPU with CUDA support (we have: RTX 2060, 8GB VRAM)
- PyTorch with CUDA (we have: PyTorch 2.5.1+cu121)
- TensorRT (bundled with ultralytics)

**Documentation**: See `docs/TENSORRT_OPTIMIZATION.md` for complete export workflow and troubleshooting

---

**Training Script Evolution** (`scripts/utils/3_train_yolo_colab.py`):
- **RECTANGULAR flag**: Toggle between square (False) and rectangular (True) training
  - `RECTANGULAR = False` → Square 640x640 (v5, CPU-optimized)
  - `RECTANGULAR = True` → Rectangular 640x1152 (v4, GPU-optimized)
- **Auto-version fetch**: Script automatically uses latest Roboflow version (no hardcoded number)
- **Preprocessing alignment**:
  - Square: Roboflow "Stretch to 640x640" + script `RECTANGULAR = False`
  - Rectangular: Roboflow "Fit within 1280x1280" + script `RECTANGULAR = True`

**Deployment Strategy**:
- **Mac (current)**: v5 square 640x640 - fast CPU inference ✅
- **PC GPU (future)**: v4 rectangular 640x1152 - accurate GPU inference
- **Switching**: Update symlink `scripts/models/best.pt` + set `config.json` → `yolo_imgsz`

**⚠️ CRITICAL**: DCC Address Class Mapping
- Classes use DCC address (CV1) as prefix: `1_Gr675_017`, `5_D645_014`, `7_E656_239`, `8_E444_056`
- **NEVER change locomotive DCC addresses after training** - breaks class mapping, requires full re-training
- Mapping in code: `DCC_TO_YOLO_CLASS = {1: 0, 5: 1, 7: 2, 8: 3}` (DCC addr → YOLO class ID)

#### Resources & Links

**YOLO**:
- ultralytics/yolov8: https://github.com/ultralytics/ultralytics
- Documentazione: https://docs.ultralytics.com
- Tutorial custom training: https://docs.ultralytics.com/modes/train/

**Annotazione**:
- LabelImg: https://github.com/heartexlabs/labelImg
- Roboflow: https://roboflow.com
- CVAT: https://www.cvat.ai

**Training online**:
- Google Colab: https://colab.research.google.com
- Kaggle Notebooks: https://www.kaggle.com/code (alternativa)

### Hardware: Webcam

**Opzioni**:
1. **IP camera acquario** ✅ **CONFERMATA FUNZIONANTE** (Tapo camera)
   - ✅ Supporta RTSP locale (rtsp://192.168.1.4:554/stream2 - 720P)
   - ✅ Integration OpenCV diretta funzionante
   - ✅ Risoluzione 1280x720 perfetta per YOLO detection
   - ✅ Nessun acquisto necessario - camera già montata sul plastico

2. **USB Webcam** (NON necessaria - IP camera sufficiente)
   - Logitech C920/C922 (€60-80) - ottima qualità, wide angle
   - Logitech C270 (€25-30) - budget, sufficiente
   - Requisiti: 720p min, 30fps, supporto Linux/Mac
   - **Nota**: IP camera Tapo funziona perfettamente, USB webcam non necessaria

### Note Implementative

**Calibrazione pixel-to-cm**:
- Posizionare oggetto noto (es. righello 30cm) sul plastico
- Calcolare rapporto pixel/cm
- Salvare calibration per future sessioni

**Object detection**:
- Train custom model su locomotive specifiche (opzionale)
- Color tracking come fallback (locomotive colori distintivi)

**Performance**:
- Processing video: 10-15 FPS sufficiente (non serve 30fps)
- Reduce resolution per performance (640x480 ok)

---

## Debug Mode - Video Feed Overlay

**Status**: ✅ Implementato (2025-01-07)
**Commit**: `47c4097` - feat: add debug mode with YOLO bbox overlay (B key toggle)

### Overview

Debug visualization overlay sul video feed per monitorare YOLO detections in real-time senza dover usare lo standalone script `track_consist_yolo.py`.

**Hotkey**: **B** (Bounding boxes) - Toggle debug overlay on/off

### Features

**Overlay Elements**:
- **Bounding boxes**: Rettangoli colorati attorno locomotive rilevate
- **Center points**: Cerchi hollow (15px radius) sui centroidi
- **Confidence labels**: Testo tipo "E656 0.87" (nome + confidence score)
- **Color coding**: Giallo (L1), Arancio (L5), Verde (L7), Rosso (L8)

**UI Integration**:
- Hint text aggiornato: `"P: Toggle Panel | B: Debug YOLO"`
- Toggle persistente (tutti i client vedono stesso stato)
- Console log: `🔍 Debug overlay toggled: visible/hidden`

### Architecture

**Backend** (`backend/video_feed.py`):
```python
# Global state
SHOW_DEBUG_OVERLAY = False

def draw_debug_overlay(frame, detections):
    """Draw bounding boxes + center points + confidence labels"""
    for det in detections:
        bbox = det.get('bbox')  # [x1, y1, x2, y2]
        position = det['position']  # [x, y]
        confidence = det['confidence']

        # Draw bbox
        if bbox:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Draw center point (hollow circle)
        cv2.circle(frame, position, 15, color, 2)

        # Draw confidence label
        label = f"{name} {confidence:.2f}"
        cv2.putText(frame, label, label_pos, ...)
```

**API Endpoint** (`backend/main.py`):
```python
@app.post("/api/toggle-debug")
async def toggle_debug():
    video_feed_module.SHOW_DEBUG_OVERLAY = not video_feed_module.SHOW_DEBUG_OVERLAY
    return {"debug_visible": video_feed_module.SHOW_DEBUG_OVERLAY}
```

**WebSocket Data** (`backend/tracking_daemon.py`):
```python
# Broadcast YOLO detections con bbox incluso
positions.append({
    'address': address,
    'name': loco_name_short,
    'position': [x, y],
    'confidence': conf,
    'bbox': [x1, y1, x2, y2]  # ← Aggiunto per debug overlay
})
```

**Frontend** (`web/src/App.jsx`):
```javascript
// B key listener
if (e.key === 'b' || e.key === 'B') {
  fetch(`${API_URL}/api/toggle-debug`, { method: 'POST' })
    .then(res => res.json())
    .then(data => console.log(`🔍 Debug overlay toggled: ${data.debug_visible ? 'visible' : 'hidden'}`));
}
```

### Known Limitations: RTSP Lag

**Problema**: Bbox mostrano posizione ~1-2s **avanti** rispetto al video visibile.

**Root Cause**:
```
┌─────────────────────────────────────────────────────────┐
│ Tracking Daemon (real-time)                            │
│   RTSP stream → YOLO inference → WebSocket JSON        │
│   ~0ms lag     ~30ms GPU        ~1ms localhost         │
│   Total: ~31ms                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Video Feed (delayed)                                    │
│   RTSP stream → encode JPEG → HTTP → browser buffer    │
│   ~0ms lag     ~20ms CPU     network  ~1-2s buffering  │
│   Total: ~1-2s                                          │
└─────────────────────────────────────────────────────────┘
```

**Perché accade**:
1. **Daemon**: 30 FPS, inference GPU velocissima, detections via WebSocket localhost
2. **Video feed**: 15-30 FPS, JPEG encoding CPU-intensive, browser bufferizza video per smooth playback
3. **Browser buffering**: Il vero colpevole (~1-2s accumulo frame per evitare stutter)

**Risultato osservato**:
- Su **PC con GPU**: Bbox "predicono il futuro" (detections real-time su video 1-2s vecchio)
- Su **Mac con CPU**: Bbox leggermente indietro (network lag Mac→PC + CPU encoding slower)

**Workaround**: Aumentare FPS video feed (15→30) riduce lag ma non elimina browser buffering.

**Alternative per zero-lag debug**:
- Usare standalone script `track_consist_yolo.py` (YOLO + video stesso loop)
- Implementare nuovo endpoint `/api/video_feed_debug` con sync perfetto (future work)

### Configuration Override

**Machine-specific FPS**: `config.local.json` (gitignored)

**Esempio PC** (GPU potente):
```json
{
  "tracking": {
    "fps": {
      "video_feed": 30
    }
  }
}
```

**Mac** (CPU-only):
- Nessun `config.local.json` → usa default 15 FPS da `config.json`

**Deep merge automatico**:
- `config_loader.py` merge `config.json` + `config.local.json`
- Override locale non committato su git (machine-specific)
- Persistente su tutti i branch (git non tocca file ignorati)

### Usage

**Enable debug overlay**:
1. Apri dashboard web
2. Espandi Video Feed panel
3. Premi tasto **B**
4. Verifica bbox colorate + pallini + confidence labels

**Disable debug overlay**:
- Premi nuovamente **B**

**Console verification**:
```
🔍 Debug overlay toggled: visible
🔍 Debug overlay toggled: hidden
```

**Note**:
- Utile per verificare YOLO detection accuracy
- Lag ~1-2s accettabile per debug purposes
- Dimostra che tracking è real-time (bbox "nel futuro" = detections fresche)

---

