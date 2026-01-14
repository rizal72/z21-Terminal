# JMRI Integration Details

Dettagli completi sulla relazione tra z21-Terminal e JMRI.

Per info essenziali, vedi main CLAUDE.md file.

---

## IMPORTANTE: z21-Terminal è un'estensione di JMRI, non un sostituto

## Dipendenze

- **JMRI è prerequisito**: z21-Terminal legge dati da file XML di JMRI
  - Roster locomotive: `~/Library/Preferences/JMRI/.../roster/*.xml`
  - Consist: `~/Library/Preferences/JMRI/.../roster/consist/consist.xml`
  - Funzioni: Definizioni F0-F28 caricate dinamicamente dal roster

## Coesistenza

- **z21-Terminal NON richiede JMRI in esecuzione**: legge solo i file XML del roster
- z21-Terminal e JMRI possono funzionare contemporaneamente (opzionale)
- Entrambi comunicano con Z21 via protocollo LAN (UDP porta 21105)
- Ultimo comando inviato ha priorità in caso di controllo simultaneo
- Eventuali conflitti si risolvono riavviando Z21 o JMRI
- **Nota polling**: Sincronizzazione funzioni/power funziona perfettamente con JMRI
  - Velocità/direzione: meglio usare solo Python O solo JMRI (non contemporaneamente)

## Complementarità

| Funzionalità | JMRI | z21-Terminal |
|--------------|------|--------------|
| Configurazione decoder (CV) | ✅ DecoderPro | ⏳ Futuro |
| Programming track | ✅ | ⏳ Futuro |
| Gestione roster/consist | ✅ | ❌ (solo lettura) |
| Controllo locomotive | ✅ Throttle UI | ✅ Controller terminale |
| Automazione/scripting | ⚠️ Jython | ✅ Python 3 |
| Controllo funzioni F0-F28 | ✅ | ✅ |
| Lettura stato locomotiva | ✅ | ✅ |

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

- **Roster directory**: `/Users/riccardosallusti/Library/Preferences/JMRI/La_mia_Ferrovia_in_JMRI.jmri/roster/`
- **Backup roster**: `/Users/riccardosallusti/Documents/Trenini/JMRI/Roster_Backup.roster`

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
