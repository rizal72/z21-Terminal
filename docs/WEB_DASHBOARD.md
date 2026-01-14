# Web Dashboard

**Status**: ✅ MVP Completed (2025-12-24)  
**Project**: z21-Terminal - BiancAlice Railway Layout

Modern mobile-first web dashboard for DCC locomotive control via Z21 LAN protocol.

---

## Web Dashboard

**Status**: ✅ **MVP COMPLETATO** (2025-12-24)
**Timeline effettiva**: 1 giorno (pianificati 2-3)
**URL locale**: http://localhost:5173

### Quick Start
```bash
# Avvia tutto (backend + frontend in tab iTerm2 separate)
z21

# Oppure separati
z21-backend    # Backend FastAPI (porta 8000)
z21-frontend   # Frontend Vite (porta 5173)

# Controller terminale CLI
z21-terminal   # Python CLI controller
```

### Development Workflow

**Vite Hot Module Replacement (HMR)**:
- ✅ Frontend: modifiche a `.jsx`, `.css` si aggiornano **automaticamente** (no restart necessario)
- ❌ Backend: modifiche a `.py` richiedono **restart manuale** del backend

**Quando riavviare**:
- Modifiche frontend (React, CSS): **NON serve riavviare** - HMR aggiorna istantaneamente
- Modifiche backend (Python): **riavvia solo backend** con `z21-backend` (o `Ctrl+C` + `z21`)

**Note**:
- Vite HMR preserva lo stato React durante l'update
- Il frontend resta connesso via WebSocket durante modifiche frontend
- Solo il backend WebSocket si disconnette/riconnette quando si riavvia il backend

### Stack Tecnologico Implementato

**Frontend**:
- **Vite 6.0** - Build tool con HMR (Hot Module Replacement)
- **React 18.3** - Framework UI component-based
- **Tailwind CSS v3.4** - Utility-first CSS (v4 causava problemi compatibilità)
- **Custom fonts**: Outfit (display), Manrope (body), JetBrains Mono (mono)

**Backend**:
- **FastAPI 0.115** - Python async framework
- **WebSocket** - Real-time bidirectional communication
- **Uvicorn** - ASGI server con auto-reload
- **Integrazione z21.py** - Libreria Z21 protocol esistente
- **roster_loader.py** - Parser JMRI XML per consist e funzioni

**Deployment**:
- Locale Mac: backend porta 8000, frontend porta 5173
- Accessibile da rete locale: http://192.168.1.xxx:5173
- Hot reload su entrambi frontend e backend

### Struttura Progetto

```
z21-Terminal/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket
│   ├── z21_manager.py       # Wrapper Z21 con gestione stato consist
│   ├── roster_loader.py     # Parser JMRI XML
│   ├── requirements.txt     # Dependencies Python
│   └── .env.example         # Config Z21 IP
│
└── web/
    ├── src/
    │   ├── App.jsx          # Main component (dual consist layout)
    │   ├── components/
    │   │   └── ConsistController.jsx  # Controller singolo consist
    │   ├── hooks/
    │   │   └── useWebSocket.js        # WebSocket hook
    │   └── index.css        # Custom styles + Tailwind
    ├── package.json
    ├── tailwind.config.js   # Custom theme "Control Room Noir"
    └── vite.config.js
```

### Features Implementate ✅

**Controllo locomotive**:
- ✅ Velocità slider 0-126 (touch-optimized, 48px thumb)
- ✅ Direzione toggle (forward/reverse)
- ✅ Funzioni F0-F28 con indicatori stato ON/OFF
- ✅ Emergency stop (toggle power on/off)
- ✅ Supporto funzioni lockable (toggle) e momentanee (auto-release 800ms)

**UI/UX**:
- ✅ Layout dual consist (consist 10 e 11)
- ✅ Track visualization con posizione treno
- ✅ Responsive design (desktop/tablet/phone)
- ✅ Dark theme "Control Room Noir" con estetica industriale
- ✅ Indicatori stato real-time (velocità, direzione, power, funzioni)
- ✅ Connection status indicator

**Real-time sync**:
- ✅ WebSocket bidirectional communication
- ✅ Initial state sync da Z21 (funzioni, velocità, direzione)
- ✅ Broadcast updates a tutti i client connessi
- ✅ Multi-device speed/direction sync (fix 2025-12-30)
- ✅ Auto-reconnect con exponential backoff

**Mobile/iOS optimizations** (2025-12-30):
- ✅ Wake Lock API per prevenire screen sleep (iOS/Android)
  - Pulsante toggle solo su mobile/tablet (nascosto desktop)
  - Richiede tap utente su Safari iOS (requisito browser)
- ✅ Header compatto su mobile
  - Solo icone senza contenitori: ⚡📶🖥️🌙
  - Gap ridotto per risparmiare spazio
  - Tablet/desktop mantengono layout completo con testo

**Gate Editor** (2025-01-07):
- ✅ Web-based gate configuration editor (Press E key or toolbar button)
- ✅ Drag & drop gates to reposition (click center, drag)
- ✅ Rotate handle (blue circle above gate)
  - Calculates delta angle from initial position
  - No snap/jump on click
- ✅ Resize handles (4 corners: nw, ne, sw, se)
  - Opposite corner stays fixed during resize
  - Respects gate rotation (transforms mouse delta to local coordinates)
  - Min size 20px to prevent collapse
- ✅ Coordinate system: camera space 1280x720 (aligned with YOLO tracking)
- ✅ Accurate video dimensions (excludes letterbox bars from objectFit: contain)
- ✅ Auto-backup: creates `config.json.backup` before save (single file, overwrites)
- ✅ UI: Centered Save/Cancel toolbar, instructions at bottom
- ✅ Desktop/tablet only (hidden on mobile <768px)
- ✅ Component: `web/src/components/GateEditor.jsx` (313 lines)

**Video Feed Controls** (2025-01-07):
- ✅ Descriptive toolbar buttons: "Δt Panel", "Debug", "Edit"
- ✅ Debug toggle (B key) with backend sync
  - Visual feedback: amber when active, grey when inactive
  - Uses backend state as source of truth (prevents desync)
- ✅ Removed keyboard hints overlay (cleaner UI)

**Integrazione JMRI**:
- ✅ Lettura roster e consist da XML JMRI
- ✅ Caricamento dinamico funzioni da roster
- ✅ Indipendente (JMRI non deve essere running)
- ✅ Routing funzioni consist: F0→lead+rear, F1-F28→lead

### Design "Control Room Noir"

**Color Palette**:
```javascript
colors: {
  'control-black': '#0a0a0a',      // Background principale
  'control-dark': '#1a1a1a',       // Panel background
  'control-grey': '#2a2a2a',       // Borders
  'signal-amber': '#ff9500',       // Primary accent
  'signal-red': '#e63946',         // Emergency/danger
  'signal-green': '#06d6a0',       // Active state
  'track-steel': '#64748b',        // Secondary text
}
```

**Typography**:
- Display: Outfit (bold, per titoli e header)
- Sans: Manrope (body text, UI)
- Mono: JetBrains Mono (numeri, codici)

**Visual Details**:
- Grain texture overlay su tutti i panel
- Signal glow effect su indicatori amber
- Touch-optimized controls (48px minimum touch target)
- Animazioni fade-in staggered per i panel

### Alias Bash Creati

File: `~/.bash_aliases`

```bash
# z21-Terminal aliases (aggiornati 2025-12-27)
alias z21-terminal='cd ~/Documents/_PROGETTI/z21-Terminal/scripts && python3 z21_controller.py'
alias z21-backend='cd ~/Documents/_PROGETTI/z21-Terminal/backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000'
alias z21-frontend='cd ~/Documents/_PROGETTI/z21-Terminal/web && npm run dev -- --host'

# Funzione z21() - Lancia backend + frontend in tab iTerm2 separate
z21() {
    cd ~/Documents/_PROGETTI/z21-Terminal
    osascript <<END
tell application "iTerm2"
    tell current window
        tell current session
            write text "cd ~/Documents/_PROGETTI/z21-Terminal/backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000"
        end tell
        create tab with default profile
        tell current session
            write text "cd ~/Documents/_PROGETTI/z21-Terminal/web && npm run dev -- --host"
        end tell
    end tell
end tell
END
}
```

### Fix Importanti Risolti

**1. Tailwind CSS v4 incompatibilità**:
- Problema: Plugin `@tailwindcss/postcss` per Tailwind v4 (beta)
- Fix: Downgrade a `tailwindcss@^3.4.0`
- Config: `postcss.config.js` usa `tailwindcss: {}`

**2. Function state sync**:
- Problema: Funzioni mostravano sempre OFF al reload
- Fix: Frontend usa `consist.functionStates?.[fn.number]` da backend
- Backend: Sync iniziale da Z21 con `get_loco_info()` in `initialize_consist()`

**3. Function control routing**:
- Problema: Comandi inviati a consist address (non funzionava)
- Fix: F0 inviato a lead+rear, F1-F28 solo a lead
- Implementato in `z21_manager.py` metodo `set_function()`

**4. Initial state loading**:
- Problema: `initial_state` message ignorava `functionStates` da backend
- Fix: Parsing corretto in `App.jsx` per usare stati Z21 reali

**5. Safari Mac animation broken** (2025-12-28):
- **Problema**: Animazioni bottoni funzioni su Safari Mac smettevano di funzionare
  - Transizione a verde: ritardo di ~1s poi snap istantaneo (no smooth animation)
  - Safari iOS e Chrome Mac funzionavano perfettamente
  - Solo Safari Mac era affetto
- **Root cause identificato**: Rimozione di `shadow-lg` e `animate-glow` da `.status-indicator`
  - Safari Mac NON riesce ad animare correttamente elementi con `transition-all` quando:
    - Shadow viene rimosso (prima c'era `shadow-lg`, poi tolto)
    - Animation viene rimossa (prima c'era `animate-glow`, poi tolto)
  - Chrome è più permissivo e gestisce la transizione comunque
- **Fix applicato**:
  - Mantenuto `shadow-lg` su `.status-indicator` (ombra sempre presente)
  - Mantenuto `animate-glow` su `.status-indicator.on` (pulse effect)
  - Safari ora anima smooth come prima
- **Lesson learned**:
  - Safari richiede proprietà CSS consistenti (shadow, animations) su elementi con `transition-all`
  - Anche se shadow/animation non cambiano valore, devono essere presenti
  - Non rimuovere mai shadow o animation da elementi che devono animare su Safari
- **Nota**: I colori dei pallini (rosso/amber) e stili bottoni NON erano il problema
  - Test incrementali confermarono che solo shadow-lg/animate-glow causavano il bug

### Debug Mobile Responsive (2025-12-25)

**Problema iniziale**: Controller overflow orizzontale su iPhone 13 mini (375px width)
- Contenuto tagliato a destra dal 60% in poi
- Necessario scrollare orizzontalmente per vedere funzioni e controlli

**Tentativi FALLITI** (da NON ripetere):

1. **Rimozione gradient con width: 200vw** - non ha risolto
   - Pensato che fosse il gradient dello slider la causa
   - Rimosso div con `width: 200vw`, ma overflow persisteva

2. **Riduzione padding** - impatto minimo
   - `p-6` → `p-4` → `p-2` → `p-0` sui `.control-panel`
   - Non ha risolto perché `grid-cols-2` divide spazio indipendentemente dal padding
   - Se container è largo 166%, ogni colonna è comunque 83% larga

3. **overflow-x: hidden** - ha rotto sticky header
   - Applicato al container principale
   - Ha nascosto overflow MA ha rotto `position: sticky` dell'header

4. **max-w-full, w-full, min-w-0 vari** - no effetto
   - Provati su vari elementi senza successo
   - Il problema era a monte (design per 600px+ su screen 375px)

5. **margin-bottom con percentuali** - non funziona con transform
   - Provato `-40%`, `-80%` sulla `.controllers-grid`
   - Le percentuali non compensano lo spazio fantasma del transform

6. **margin-bottom in px troppo aggressivi**
   - `-500px` → troppo poco (footer 1000px sotto)
   - `-1000px` → troppo poco ancora
   - `-1500px` → footer sparito (troppo)

**Soluzione FUNZIONANTE per iPhone 13 mini** (`/web/src/index.css`):
```css
@media (max-width: 390px) {
  .controllers-grid {
    transform: scale(0.6);
    transform-origin: top left;
    width: 166.67%; /* Compensa lo scale 0.6 (100 / 0.6 = 166.67) */
    margin-bottom: -1110px !important; /* Compensa spazio verticale fantasma */
  }

  .controllers-grid > * + * {
    margin-top: 60px; /* Spazio tra controller (60 * 0.6 = ~36px visibili) */
  }
}
```

**Valori critici**:
- Scale: `0.6` (60%) - dimensione minima per leggibilità touch
- Width compensation: `166.67%` - matematica: 100 / 0.6 = 166.67
- Margin-bottom: `-1110px` - trovato iterativamente (partendo da -500, poi -700, -950, -1075, -1110)
- Spacing tra controller: `60px` - dopo scale diventa ~36px visivamente

**Problema aggiuntivo scoperto**: Dropdown overflow su iPad landscape

Quando controller affiancati (iPad landscape con breakpoint `lg:`):
- Dropdown `select` sbordava insieme all'icona del treno
- Container troppo stretto per entrambi

**Fix dropdown/icona** (`/web/src/components/ConsistController.jsx`):
```jsx
<div className="flex items-center gap-2"> {/* era gap-3 (12px) */}
  <select className="flex-1 min-w-0 ..."> {/* min-w-0 è CRITICO */}
    ...
  </select>
  <div className="... w-10 h-10 ... flex-shrink-0"> {/* era w-12 (48px) */}
    {/* Train icon */}
  </div>
</div>
```

**Dettagli fix**:
1. **Gap ridotto**: `gap-3` (12px) → `gap-2` (8px)
2. **Icona più piccola**: `w-12` (48px) → `w-10` (40px)
3. **min-w-0 sul select**: CHIAVE per permettere compressione
   - Default flex items: `min-width: auto` impedisce riduzione
   - Con `min-w-0`: dropdown può comprimersi sotto dimensione contenuto
4. **flex-shrink-0 su icona**: impedisce deformazione

**Header responsive** (`/web/src/App.jsx`):
- Mobile (<768px): solo "z21"
- iPad mini+ (≥768px): "z21 Terminal" + sottotitolo "DCC Locomotive Controller"
- Desktop (≥1024px): titolo più grande (text-3xl)

**Test residuo da fare**:
- ⚠️ Su mobile iPhone 13 mini sborda ancora dal 70% in poi (non risolto completamente)
- Rimuovendo lo scale, overflow persiste
- Causa probabile: altri elementi oltre dropdown (slider? funzioni grid? padding generale?)
- TODO: investigare ulteriormente per trovare soluzione senza scale

**Commit**: `1525a38` - "fix: responsive layout for mobile and iPad landscape"

### Soluzione Definitiva Mobile Overflow (2025-12-26) ✅

**PROBLEMA RISOLTO**: Identificata la vera causa dell'overflow orizzontale su iPhone 13 mini.

**Root cause**: Il dropdown `<select>` con option contenenti testo lungo (es. "Consist 10: Gr.675 017 + D645 014") espandeva il suo contenuto oltre i limiti del viewport, causando overflow del 166%.

**Soluzione applicata** (`/web/src/components/ConsistController.jsx`):
```jsx
<div className="flex items-center gap-2 overflow-hidden">
  <select
    className="flex-1 min-w-0 max-w-full ... overflow-hidden text-ellipsis"
    style={{ width: '100%' }}
  >
```

**Chiavi del fix**:
1. `overflow-hidden` sul flex container (previene espansione oltre i limiti)
2. `min-w-0` sul select (permette compressione sotto la dimensione del contenuto)
3. `max-w-full` sul select (forza rispetto della larghezza parent)
4. `overflow-hidden text-ellipsis` (tronca il testo visibile con ...)
5. `width: 100%` inline style (forza larghezza esplicita)

**Keyboard shortcuts hint fix**:
```jsx
<div className="flex flex-wrap justify-center gap-x-2 gap-y-1">
  <span className="whitespace-nowrap">\ = Both</span>
  <span className="whitespace-nowrap">• Shift+\ = This</span>
  <span className="whitespace-nowrap">• 1-9 = 10-90%</span>
  <span className="whitespace-nowrap">• 0 = 100%</span>
</div>
```
- Sostituito testo unico con flex-wrap chunks
- Ogni chunk con whitespace-nowrap va a capo automaticamente

**Risultato**:
- ✅ Rimosso workaround `scale(0.6)` da `/web/src/index.css`
- ✅ Layout naturale senza trasformazioni CSS
- ✅ Nessun overflow orizzontale su iPhone 13 mini (375px)
- ✅ Tutti i controller, funzioni, slider funzionano perfettamente

**Lesson learned**: Il problema era nel dropdown, non nel layout generale. Lo `scale(0.6)` mascherava il sintomo ma non risolveva la causa.

### Workflow Operativo

**1. Avvio dashboard**:
```bash
z21    # Lancia backend e frontend in tab iTerm2 separate
```

**2. Accesso**:
- Locale: http://localhost:5173
- Rete locale: http://192.168.1.xxx:5173 (es. da iPad)

**3. Controllo**:
- Slider velocità per muovere treni
- Toggle direzione per cambiare verso
- Click funzioni F0-F28 per luci, suoni, etc.
- Emergency stop per togliere/ripristinare corrente

**4. Multi-device**:
- Apri dashboard su più dispositivi contemporaneamente
- Tutti i client si sincronizzano in real-time via WebSocket
- Esempio: iPad controlla consist 10, Phone controlla consist 11

### Soluzione Immediata (pre-dashboard)
**Terminali multipli** per controllo simultaneo di più locomotive:
```bash
# Terminale 1 - Consist interno
python3 z21_controller.py 10

# Terminale 2 - Consist esterno
python3 z21_controller.py 11

# Terminale 3 - Loco singola
python3 z21_controller.py 3
```

### Strategia: Complementare, Non Sostitutivo

**JMRI**: Setup e configurazione
- ✅ Configurazione decoder CV (DecoderPro)
- ✅ Programming track
- ✅ Gestione roster/consist
- ✅ Tool maturo e completo

**z21-Terminal Dashboard**: Operations e controllo
- ✅ Controllo operativo quotidiano
- ✅ UI moderna mobile-first
- ✅ Automazioni custom Python 3
- ✅ Indipendente (JMRI non deve running)
- ✅ Lightweight (no Java)

### Vantaggi Unici Dashboard Custom

#### 1. Specializzazione sul Plastico
- Layout grafico dei 2 tracciati (interno/esterno)
- Consist preconfigurati (10 e 11)
- Funzioni sound specifiche per decoder installati
- Scenari custom: "Partenza sincronizzata", "Incrocio", "Notte", "Show sound"

#### 2. UI Moderna e Mobile-First
- Design responsive tablet/phone
- Touch-friendly: slider grandi, bottoni touch
- Progressive Web App (installabile su iPad home screen)
- Dark mode nativo
- Animazioni fluide (React/Vue)

#### 3. Multi-utente/Multi-device
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   iPad      │  │   Phone     │  │   Laptop    │
│  Consist 10 │  │  Consist 11 │  │  Overview   │
└─────────────┘  └─────────────┘  └─────────────┘
```
- Ogni device controlla loco/consist diverso
- Vista "director" su laptop per monitoring
- Sync real-time via WebSocket

#### 4. Indipendenza da JMRI
- Legge solo XML roster (non richiede JMRI running)
- Più leggero: Python + FastAPI vs Java JMRI
- Startup rapido: `python3 dashboard.py` → browser

#### 5. Automazioni Python 3
- Scenari preconfigurati per il plastico
- Integrazione diretta con z21.py library
- Estensibile facilmente (no Jython)

#### 6. Analytics & Logging
- Storico velocità/direzione
- Log funzioni sound
- Statistiche: km percorsi, tempo operativo
- Export CSV per analisi

### Stack Tecnologico Proposto

**Backend:**
- FastAPI (Python 3) - REST API + WebSocket
- Riuso z21.py library (già completa)
- SQLite per logging/analytics (opzionale)

**Frontend:**
- React/Vue.js (da decidere)
- TailwindCSS per styling
- Progressive Web App
- WebSocket per real-time sync

**Deployment:**
- Esecuzione locale (Mac)
- Accessibile via WiFi da tablet/phone
- Porta 8000 (configurabile)

### Confronto JMRI Web vs Dashboard Custom

| Feature | JMRI Web | z21-Terminal Dashboard |
|---------|----------|------------------------|
| Configurazione decoder CV | ✅ | ❌ |
| Gestione roster | ✅ | ❌ (read-only) |
| Controllo operativo quotidiano | ⚠️ Possibile | ✅✅✅ Ottimizzato |
| Mobile/tablet UI | ⚠️ Non ottimale | ✅ Mobile-first |
| Automazioni custom | ⚠️ Jython script | ✅ Python 3 integrato |
| Scenari plastico-specifici | ❌ | ⏳ Pianificati |
| Lightweight (no Java) | ❌ | ✅ |
| Richiede JMRI running | ✅ | ❌ |
| Multi-device sync | ⚠️ Limitato | ✅ WebSocket real-time |

### Features Future (Post-MVP)

- [ ] Scenari preconfigurati per plastico
- [ ] Analytics e logging (storico velocità, funzioni, km percorsi)
- [x] ~~Progressive Web App installabile (iPad home screen)~~ ✅ COMPLETATO (2025-12-26)
- [ ] Voice control (Alexa/Google Home integration)
- [x] ~~Tailscale Serve permanente~~ ✅ CONFERMATO: configurazione persiste dopo reboot (2025-12-26)
  - Backend esposto su porta 8000, frontend su porta 5173
  - Comando verifica: `tailscale serve status`
  - Accessibile via HTTPS: `https://mbp16diriccardo.tail9350d7.ts.net`

---
---
