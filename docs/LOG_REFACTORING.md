# Log Refactoring - Design Definitivo

**Data**: 2025-01-09
**Status**: ✅ **COMPLETATO** (commit 99d46cf, merged to main 040458e)

## Obiettivo
Refactoring completo del sistema di logging da approccio "low-level" (costanti importate) a design pattern centralizzato con mapping PREFIX → COLOR.

## Design Pattern Finale

### File `backend/log_colors.py`:

```python
"""
ANSI color codes for log output prefixes and status keywords.
Compatible with dark and light terminal backgrounds.
Centralized mapping for easy maintenance.
"""

# Mapping PREFIX → COLOR (single source of truth)
PREFIXES = {
    '[INIT]': '\033[97m',    # White bright - startup (importante, alta visibilità)
    '[SHUT]': '\033[35m',    # Viola/Magenta normale - shutdown
    '[ERROR]': '\033[91m',   # Red bright - errori critici (file not found, connection failed, etc.)
    '[WARN]': '\033[93m',    # Yellow bright - warnings
    '[STOP]': '\033[91m',    # Red bright - emergency/stop commands
    '[CV]': '\033[91m',      # Red bright - operazioni CV critiche
    '[COMP]': '\033[95m',    # Magenta bright - auto-compensation
    '[VIRT]': '\033[36m',    # Cyan normale - virtual mode speed updates (frequente, tecnico)
    '[SYNC]': '\033[92m',    # Green bright - sync operations
    '[DETECT]': '\033[96m',  # Cyan bright - YOLO detection/tracking (era [TRACK])
    '[GATE]': '\033[94m',    # Blue bright - gate crossings
    '[WS]': '\033[34m',      # Blue normale - websocket connections
    '[OVFL]': '\033[95m',    # Magenta bright - overflow
}

RESET = '\033[0m'

# Status keyword colors (unchanged)
STATUS_GREEN = '\033[92m'   # SYNCED
STATUS_YELLOW = '\033[93m'  # WARNING
STATUS_RED = '\033[91m'     # CRITICAL

def log(prefix, message):
    """
    Centralized logging with colored prefix.

    Args:
        prefix: One of the keys in PREFIXES dict (e.g., '[ERROR]', '[INIT]')
        message: Log message text

    Example:
        log('[ERROR]', 'File not found')
        log('[INIT]', 'Backend starting...')
    """
    color = PREFIXES.get(prefix, '')
    print(f"{color}{prefix}{RESET} {message}")

def colorize_status(text: str) -> str:
    """
    Colorize status keywords in text (SYNCED, WARNING, CRITICAL).
    Unchanged from current implementation.
    """
    text = text.replace('SYNCED', f'{STATUS_GREEN}SYNCED{RESET}')
    text = text.replace('WARNING', f'{STATUS_YELLOW}WARNING{RESET}')
    text = text.replace('CRITICAL', f'{STATUS_RED}CRITICAL{RESET}')
    return text
```

### Utilizzo nei file:

```python
# Opzione 1: Import funzione
from log_colors import log

log('[ERROR]', 'File not found')
log('[INIT]', 'Backend starting...')

# Opzione 2: Import modulo (SE serve accesso a RESET, colorize_status, etc.)
import log_colors

log_colors.log('[WARN]', 'Camera disconnected')
```

## Vantaggi del nuovo design

1. ✅ **Single source of truth**: Cambi colore in 1 solo punto (PREFIXES dict)
2. ✅ **Aggiungi prefix facilmente**: Basta aggiungere entry al dict
3. ✅ **Import più semplice**: `from log_colors import log` invece di importare N costanti
4. ✅ **Manutenibilità**: Modifiche future in 1 file invece di 5+ files
5. ✅ **Consistenza**: Impossibile usare colori sbagliati per prefix

## Cambiamenti rispetto allo stato attuale

### Nuovi prefix:
- **[ERROR]** - Per errori critici (file not found, JSON invalid, connection failed)
  - Attualmente marcati come [WARN] ma sono veri errori
  - Colore: Red bright (91m) - alta visibilità

- **[STOP]** - Per emergency stop e stop commands
  - Attualmente marcati come [COMP] ma non sono compensation
  - Colore: Red bright (91m) - sicurezza critica

### Rinominazioni:
- **[TRACK] → [DETECT]** - YOLO detection/tracking
  - Motivo: "Track" ambiguo (tracciamento vs binario/tracciato ferroviario)
  - [DETECT] più chiaro e comprensibile (detection locomotive)

### Colori modificati:
- **[INIT]**: Cyan dim → **White bright** (97m)
  - Motivo: Startup messages importanti, alta visibilità su dark/light terminal

- **[SHUT]**: Cyan dim → **Viola** (35m)
  - Motivo: Differenziare da altri prefix, shutdown è evento speciale

- **[WS]**: Cyan dim → **Blue normale** (34m)
  - Motivo: Differenziare da altri prefix, network-related

- **[WARN]**: Cyan dim → **Yellow bright** (93m) ✅ GIÀ FATTO
  - Motivo: Warning deve essere visibile, giallo standard

## Files da modificare

### Backend files:
1. `backend/log_colors.py` - Refactor completo con nuovo design
2. `backend/main.py` - Replace all print statements
3. `backend/z21_manager.py` - Replace all print statements
4. `backend/tracking_daemon.py` - Replace all print statements + [TRACK]→[DETECT]
5. `backend/tracking_manager.py` - Replace all print statements
6. `backend/config_loader.py` - Replace all print statements
7. `backend/video_feed.py` - Replace all print statements + errori → [ERROR]
8. `backend/tracking/yolo_tracker.py` - Replace all print statements + [TRACK]→[DETECT]
9. `backend/tracking/rtsp_handler.py` - Replace all print statements + errori → [ERROR]

### Pattern da sostituire:
```python
# OLD (low-level)
from log_colors import CYAN, CYAN_DIM, YELLOW, RESET
print(f"{CYAN}[TRACK]{RESET} message")
print(f"{YELLOW}[WARN]{RESET} message")

# NEW (centralized)
from log_colors import log
log('[DETECT]', 'message')
log('[WARN]', 'message')
```

### Casi speciali - Emergency stop:
```python
# OLD
print(f"{MAGENTA}[COMP]{RESET} Emergency stop: all consists stopped (compensation reset)")
print(f"{MAGENTA}[COMP]{RESET} STOP: both locos set to 0 (compensation reset)")

# NEW
log('[STOP]', 'Emergency stop: all consists stopped (compensation reset)')
log('[STOP]', 'STOP: both locos set to 0 (compensation reset)')
```

### Casi speciali - Errori critici:
```python
# OLD
print(f"{YELLOW}[WARN]{RESET} ERROR: Camera config not found")
print(f"{YELLOW}[WARN]{RESET} ERROR: Invalid JSON")
print(f"{YELLOW}[WARN]{RESET} Failed to connect to Z21")

# NEW
log('[ERROR]', 'Camera config not found')
log('[ERROR]', 'Invalid JSON in camera config')
log('[ERROR]', 'Failed to connect to Z21')
```

## Stima tempi
- **Refactor log_colors.py**: ~5 minuti
- **Replace pattern in 9 files**: ~15 minuti
- **Test manuale**: ~2-3 minuti
- **TOTALE**: ~20-25 minuti

## Note importanti
- **White (97m)** funziona su dark/light terminal:
  - Dark terminal: bianco brillante ⚪ (alta visibilità)
  - Light terminal: nero/scuro ⚫ (auto-convertito per leggibilità)

- **[VIRT]** rimane Cyan normale (36m):
  - Log molto frequente (ogni cambio velocità)
  - Non deve essere troppo visibile (tecnico, bassa priority)

- **colorize_status()** resta invariato:
  - SYNCED/WARNING/CRITICAL keywords colorati come prima
  - Usato per Δt status in COMP/SYNC logs

## Priorità implementazione
1. ✅ Refactor `log_colors.py` con nuovo design
2. ✅ Sostituire pattern in tutti i 9 files
3. ✅ [TRACK] → [DETECT] rinomina
4. ✅ Emergency stop → [STOP]
5. ✅ Errori critici → [ERROR]
6. ✅ Test manuale log output

---

## ✅ Implementazione Completata (2025-01-09)

### Risultati

**Files refactored** (9 totali):
- ✅ `backend/log_colors.py` - NEW file con PREFIXES mapping + log() helper
- ✅ `backend/config_loader.py`
- ✅ `backend/main.py`
- ✅ `backend/tracking/rtsp_handler.py`
- ✅ `backend/tracking/yolo_tracker.py`
- ✅ `backend/tracking_daemon.py`
- ✅ `backend/tracking_manager.py`
- ✅ `backend/video_feed.py`
- ✅ `backend/z21_manager.py`

**Commit**: `99d46cf` - refactor: centralized logging system with PREFIX→COLOR mapping
**Merged to main**: `040458e`

### Cambiamenti Effettuati

1. **Nuovo design centralizzato**:
   - Single source of truth: `PREFIXES = {[PREFIX]: COLOR}` dict
   - Helper function: `log(prefix, message)`
   - Import semplificato: `from log_colors import log`

2. **Nuovi prefixes**:
   - `[ERROR]` - Errori critici (Red bright 91m)
   - `[STOP]` - Emergency stop (Red bright 91m)

3. **Rinominazioni**:
   - `[TRACK]` → `[DETECT]` - Più chiaro per YOLO detection

4. **Colori aggiornati**:
   - `[INIT]`: White bright (97m) - Alta visibilità startup
   - `[SHUT]`: Purple (35m) - Distintivo per shutdown
   - `[WS]`: Blue (34m) - Network operations
   - `[WARN]`: Yellow bright (93m) - Standard warning

5. **Fix aggiuntivi**:
   - Auto-compensation toggle ora salva su config.json
   - Log sempre visibile (non più sotto debug_enabled)
   - Prefix `[COMP]` per consistency

### Tempo Effettivo

**Stimato**: 20-25 minuti
**Effettivo**: ~25 minuti (usando sed per velocità + fix syntax errors)

### Testing

- ✅ Backend riavviato con uvicorn --reload
- ✅ Tutti i log visibili con nuovi colori
- ✅ Auto-compensation toggle con log e persistenza
- ✅ Python syntax check passed su tutti i files

### Benefici Confermati

- ✅ Manutenibilità: cambiare colore in 1 punto invece di 5+ files
- ✅ Consistenza: impossibile usare colori sbagliati per prefixes
- ✅ Scalabilità: aggiungere nuovo prefix = 1 riga nel dict
- ✅ Import puliti: 1 import invece di N costanti

---

**Decisione finale**: Approvato per implementazione → ✅ COMPLETATO
**Prossimo step**: Procedere con refactoring completo → ✅ FATTO
