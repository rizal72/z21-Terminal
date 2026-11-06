# JMRI Integration Details

Dettagli completi sulla relazione tra z21-Terminal e JMRI.

Per info essenziali, vedi `AGENTS.md`.

---

## IMPORTANTE: z21-Terminal è sempre più indipendente da JMRI

### ✅ Già Indipendente (v1.0.0)

- **CV67-94 Speed Table**: Stored in `data.db` (locomotive_speed_table table), editable via web UI
- **CV19 Consist Management**: Virtual/DCC Mode toggle writes CV19 automatically
- **Locomotive Metadata**: `config.json` unified (name, decoder, color, cv_profiles)
- **Consist Configuration**: `config.json` (lead_address, rear_address, virtual_mode)
- **Consist CRUD**: Create/edit/delete consists via web UI

### ❌ Dipendenza Rimasta

- **Creazione di una locomotiva nuova**: si fa in DecoderPro (indirizzo DCC,
  decoder, CV), poi `scripts/utils/import_single_locomotive.py` la porta in
  `config.json` e in `data.db`. Non e' una lettura a runtime.
- **Reimport CV67-94**: `POST /api/speed-table/reimport/{consist_id}` legge
  l'XML JMRI, quindi e' un'operazione da Mac; sul PC non trova il roster e
  restituisce `None`.

Le function labels F0-F28 stanno in `config.json`
(`locomotives[address]['functions']`): non sono piu' lette dal roster.

**Nota**: JMRI serve solo per il setup iniziale di una locomotiva, mai durante
l'uso quotidiano.

## Coesistenza

- **z21-Terminal NON richiede JMRI**: il roster viene da `config.json`; gli XML JMRI sono solo il fallback quando `config.json` non ha locomotive
- z21-Terminal e JMRI possono funzionare contemporaneamente (opzionale)
- Entrambi comunicano con Z21 via protocollo LAN (UDP porta 21105)
- Ultimo comando inviato ha priorità in caso di controllo simultaneo
- Eventuali conflitti si risolvono riavviando Z21 o JMRI
- **Nota polling**: Sincronizzazione funzioni/power funziona perfettamente con JMRI
  - Velocità/direzione: meglio usare solo Python O solo JMRI (non contemporaneamente)

## Complementarità

| Funzionalità | JMRI | z21-Terminal |
|--------------|------|--------------|
| Configurazione decoder (CV) | ✅ DecoderPro | ✅ **CV67-94 speed table** (v1.0.0) |
| **CV19 consist management** | ✅ DecoderPro | ✅ **Virtual/DCC Mode toggle** |
| Programming track | ✅ | ⏳ Futuro |
| Gestione roster/consist | ✅ | ✅ **Consist CRUD** (create/edit/delete) |
| Controllo locomotive | ✅ Throttle UI | ✅ Controller terminale + Web Dashboard |
| Automazione/scripting | ⚠️ Jython | ✅ Python 3 |
| Controllo funzioni F0-F28 | ✅ | ✅ |
| Lettura stato locomotiva | ✅ | ✅ |
| **Function labels F0-F28** | ✅ XML roster | ✅ `config.json` |

## Workflow Operativo

### 1. Setup iniziale (JMRI DecoderPro)

- Configura decoder su programming track
- Aggiungi locomotive al roster
- Crea consist se necessario
- Programma CV (speed matching, sound, ecc.)

### 2. Uso quotidiano (z21-Terminal)

- Controllo rapido da tastiera
- Automazione con script Python
- Testing e debug

### 3. Manutenzione (JMRI DecoderPro)

- Modifica CV esistenti
- Aggiornamento configurazioni
- Gestione roster

## File di Configurazione JMRI

### Percorsi

- **Roster directory**: `/Users/<username>/Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster/`
- **Backup roster**: `/Users/<username>/Documents/<layout-name>/JMRI/Roster_Backup.roster`

### Formato File Roster

- File XML per locomotiva
- Contiene tutte le CV configurate
- Naming: `Nome_Locomotiva.xml`
- Backup automatici: `*.xml.bak`

## API JMRI

### Endpoints Testati (2025-12-17)

- **Roster**: `http://localhost:12080/json/roster/` (✅ funzionante)
- **RosterEntry**: `http://localhost:12080/json/rosterEntry/<nome>` (✅ funzionante)
- **Power**: `http://localhost:12080/json/power` (✅ funzionante)
- **Consists**: `http://localhost:12080/json/consists` (✅ funzionante)
- **System Connections**: `http://localhost:12080/json/systemConnections` (✅ funzionante)
- **Throttle**: ❌ Richiede WebSocket (non semplice HTTP REST)

### Limitazioni Note

- **Throttle control**: Richiede WebSocket, non disponibile via REST API
- **CV Read/Write**: Non accessibile via REST API standard
- Decoder Hornby TXS (loco 7): NO lettura CV in operations mode

### Alternative per Controllo Locomotive

- **Protocollo Z21 LAN** (UDP porta 21105) - funzionante e testato ✅
- **JMRI WebSocket** (porta 12080) - da implementare
- **WiThrottle protocol** (porta 12090) - non testato
