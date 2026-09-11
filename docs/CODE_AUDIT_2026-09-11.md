# Code Audit - 2026-09-11 (pi-lens full scan)

**Versione auditata**: v1.0.0
**Strumenti**: pi-lens (review graph + LSP) con runner Pyright, typescript-language-server, ast-grep, Semgrep
**Scope**: `backend/` (32 file) + `web/src` (27 file), scansione full in sola lettura
**Status codice**: nessuna modifica apportata (sessione di audit)

---

## Executive Summary

Prima sessione con pi-lens installato. Risultato chiave: **i problemi di typing backend noti sono confermati e invariati** rispetto al baseline Pyright di gennaio 2026 (26 errori deferiti, audit v0.9.11). Il vecchio documento `docs/PYRIGHT_ANALYSIS.md` e` stato assorbito e consolidato in questo file (sezione A) e rimosso per evitare duplicazioni. Il valore nuovo di questo audit sta in tre aree mai coperte prima:

1. **Sicurezza backend** (4 findings Semgrep, mai auditati)
2. **Qualita frontend** (109 warning su 27 file, mai auditati)
3. **Vista strutturale** (review graph: hub, cicli, complessita)

**Numeri grezzi**:

| Area | Errori bloccanti | Warning/qualita | Note |
| --- | --- | --- | --- |
| backend | 22 veri (~49 segnalati) | 13 | ~27 segnalazioni = falso rumore venv |
| web/src | 0 | 109 | tutti warning qualita/leggibilita |

---

## Nota critica: rumore dell'ambiente di scan (RISOLTA 2026-09-11)

Il rumore era Pyright fuori dal venv (~27 falsi `reportMissingImports`: `fastapi`, `cv2`, `numpy`, `ultralytics`, `websockets`, `z21`, `uvicorn`). Risolto con due config:

- `pyrightconfig.json` (root): aggiunti `venvPath: "."` + `venv: "venv"`
- `backend/pyrightconfig.json` (NUOVO): pi-lens tratta `backend/` come project root per i file lì sotto (log tool-cwd: `dispatch-root`), quindi serve una config in backend con `venvPath: ".."` che allinea CLI e LSP indipendentemente dal cwd

Baseline reale post-config: **15 errori**, poi **12** dopo il `cast(Any, ...)` su `results` (63aa397, chiude i 3 errori `result.obb/.boxes` di typing ultralytics). Residuo: video_feed 6 + downsampling 6 (MODERATE deferiti). Nota: i 2 `possibly unbound` in speed_table.py presenti nel vecchio audit NON compaiono più col Pyright del venv (probabile drift/inferenza migliorata); l'errore è sparito anche dalla scansione attuale.

Nota tecnica: la sessione pi-lens corrente mostra ancora gli import errors perche il server Pyright e`stato spawnato all'avvio SENZA la nuova config; un riavvio di sessione li elimina. Il gate CLI (authoritativo) e` gia` pulito.

---

## Backend - problemi reali

### A. Baseline Pyright noto (audit v0.9.11, gennaio 2026 - assorbito)

Questi NON sono scoperte nuove: sono il debito accettato a gennaio 2026 nel vecchio PYRIGHT_ANALYSIS.md (59 -> 26 errori, -56%, zero breaking changes), qui consolidato. La riduzione da 59 a 26 fu ottenuta in 4 fasi con zero breaking changes: fix import (pyrightconfig.json extraPaths), guard su Z21Manager (enable/disable_virtual_mode, toggle_test_mode), validazione WebSocket handlers, fix single-file (broadcast.py, speed_table.py, tracking_daemon.py).

| File | Errori | Categoria | Rischio | Status |
| --- | --- | --- | --- | --- |
| services/data_db.py | 9 | defaultdict + lambda: inferenza tipi (`get_analytics_summary`) | ALTO | deferito (serve TypedDict + test) |
| video_feed.py | 6 | return None su firma `-> str` + chiavi dict non validate (`draw_detections`) | MEDIO | deferito |
| services/downsampling.py | 6 | LTTB: indice `int | None` (edge case bucket vuoto) | MEDIO | deferito |
| routers/speed_table.py:693-694 | 2 | `vstart_int`/`vhigh_int` possibly unbound | BASSO | RISOLTO in venv-scan: non piu` presenti col Pyright del venv |
| tracking/yolo_tracker.py:245,168 | 2 | `yolo_obb` unbound; None su str | BASSO | RISOLTO 2026-09-11 (commit fix LOW risk) |
| tracking_manager.py:97 | 1 | attributo `DataDB.update_consist_auto_compensation` non risolto | BASSO | RISOLTO 2026-09-11: era un BUG vero, il metodo non esiste; sostituito con `DataDB.set_auto_compensation` (data_db.py:998). Il percorso di fallback "modello YOLO mancante" sarebbe crashato con AttributeError |
| services/speed_table_helpers.py:111 | 1 | None su Dict | BASSO | RISOLTO 2026-09-11 (`Optional[Dict[int, Dict]] = None`) |
| tracking/yolo_tracker.py:407,441 | 3 | `result.obb`/`result.boxes` su tipo dedotto Tensor | LIBRERIA | deferito: typing di ultralytics, non fixabile con guard (baseline noto dal changelog 2026-09-10) |

#### A.0 Stato di esecuzione del backlog storico (verificato su git + codice attuale)

Cosa fu davvero eseguito del vecchio audit e cosa resta aperto:

| Parte del vecchio audit | Stato | Evidenza |
| --- | --- | --- |
| Riduzione 59 -> 26 (fasi 1-4: import, guard Z21Manager, WS handlers, fix single-file) | ESEGUITA | commit af02676 (2026-01-23) "fix type hints Phase 2"; la scansione attuale non segnala piu` quei problemi |
| Backlog differito: LOW risk (A.4) | APERTO | verificato sul codice: vstart_int/vhigh_int ancora unbound, mai toccati da git |
| Backlog differito: MODERATE video_feed.py | APERTO | riga 74 ancora `-> str` (Optional mai applicato) |
| Backlog differito: MODERATE downsampling.py | APERTO | guard max_area_point assente dal codice |
| Backlog differito: HIGH data_db.py TypedDict | APERTO | 9 errori ancora presenti in scansione |

Storie parallele (non provenienti da questo audit): modularizzazione main.py 2340 -> 753 righe (REFACTOR_PLAN.md, eseguita gennaio 2026, PRIMA dell'audit v0.9.11); FRONTEND_REFACTOR_PLAN solo in minima parte eseguito (AnalyticsPanel resta monolitico); sicurezza (sezione B) mai auditata prima di oggi, interamente in sospeso.

#### A.1 ALTO RISCHIO: services/data_db.py (9 errori) - `get_analytics_summary`

**Causa radice**: Pyright non inferisce i tipi di `defaultdict(lambda: {'delta_t_values': [], 'synced_count': 0, ...})`. Il lambda restituisce `dict[str, int | list[Any]]` (unione di tutti i value), quindi ogni accesso ai dizionari e` tipizzato come `int | list[Any]` invece del tipo specifico per chiave.

**Perche`e` critico**: la funzione calcola le statistiche del dashboard (avg/min/max Delta-t, trend LEAD/REAR FASTER, synced percentage, raccomandazioni speed table). Se rotta: statistiche errate, raccomandazioni inaffidabili, errori solo a runtime.

**Fix corretto** (deferito perche` richiede refactoring strutturale + test):

```python
from typing import TypedDict

class ConsistData(TypedDict):
    delta_t_values: list[float]
    synced_count: int
    warning_count: int
    critical_count: int

consist_data: defaultdict[int, ConsistData] = defaultdict(...)
```

**Anti-pattern da evitare**: `# type: ignore` nasconde il problema senza risolverlo, blocca il refactoring futuro e inutilizza l'autocompletamento.

**Quando fixare**: con la test suite analytics (non esiste oggi) o al refactoring analytics v1.1.0. Il codice funziona in produzione, meglio 26 errori documentati che 0 errori + bug in produzione.

#### A.2 MEDIO RISCHIO: video_feed.py (6 errori)

**Problema 1** (`load_camera_config`, righe 73-101): firma dichiara `-> str` ma ritorna `None` su errore. Fix banale (1 riga): `-> Optional[str]`; propagazione: tutti i call site devono aggiungere il check None.

**Problema 2** (`draw_detections`, righe 286-296): chiavi dei dict detection non validate prima dell'uso; `address` puo` essere None e viene passato a `COLORS.get(address, ...)`. Fix: guard`if address is None: continue` + cast `int(address)` (3 righe). Nota: cambia il comportamento (detection senza address viene skippata invece di glitch visivo) - testare con dati malformati.

**Quando fixare**: con test video feed o refactoring tracking_daemon output. Effort ~30 min.

#### A.3 MEDIO RISCHIO: services/downsampling.py (6 errori) - algoritmo LTTB

**Causa radice**: `max_area_point` inizializzato a None; se `range_start == range_end` (bucket vuoto con `max_points` piccoli) il loop interno non gira e resta None -> `data[None]` = IndexError a runtime.

**Fix**: guard dopo il loop: `if max_area_point is None: max_area_point = range_start` (fallback al primo punto del bucket). Testare con max_points 100/500/1000/2000 e edge case `len(data) <= max_points`. Criticita` bassa (solo rendering grafici, fail-safe esiste). Effort ~30-45 min.

#### A.4 BASSO RISCHIO: Others (6 errori, fix ~15-20 min, zero effetti collaterali)

| File | Errore | Fix |
| --- | --- | --- |
| routers/speed_table.py:693-694 | `vstart_int`/`vhigh_int` possibly unbound | inizializzare prima del blocco try |
| tracking/yolo_tracker.py:245 | `yolo_obb` unbound | guard + inizializzazione |
| tracking/yolo_tracker.py:168 | None su parametro str | guard check |
| tracking_manager.py:97 | attributo classe non risolto | type annotation (o confermare metodo dinamico) |
| services/speed_table_helpers.py:111 | None su Dict | Optional return type |

#### A.5 Matrice di rischio (dal vecchio audit)

| Criterio | ALTO (data_db) | MEDIO (video/downsampling) | BASSO (others) |
| --- | --- | --- | --- |
| Complessita fix | TypedDict + refactoring | firma/guard + edge case | guard 3 righe |
| Effetti collaterali | cambio data model | skip dati invalidi | zero |
| Test necessari | obbligatori | consigliati | facoltativi |
| Business critical | analytics dashboard | video/charts | validazione input |
| Effort | 1-3 h | 30-45 min | 15-20 min |
| Priorita | al refactoring v1.1.0 | con test coverage | anytime |

### B. Sicurezza (Semgrep) - NOVITA di questo audit

Mai auditati prima. Valutare nel contesto: applicazione single-user su LAN domestica + Tailscale, non esposta a internet pubblico.

| File | Linea | Finding | Valutazione |
| --- | --- | --- | --- |
| main.py | 473 | CORS wildcard `*` | Accettabile in LAN; da rivedere se il backend diventa raggiungibile oltre tailnet |
| roster_loader.py | 31, 125, 200 | XML nativo vulnerabile a XXE (input: roster JMRI/RoCoFo) | Fix consigliato: `defusedxml` (3 punti, costo minimo). Input semi-fidato, rischio reale basso ma non zero |
| routers/config.py | 536 | URL costruito da dato utente (pattern SSRF) | Verificare la sorgente del dato: se e` la config locale dell'operatore, rischio trascurabile |
| services/data_db.py | 854 | SQL con concatenazione | VERIFICATO falso positivo (vedi B.1) |

#### B.1 Esito verifiche puntuali (2026-09-11)

| Finding | Verdetto | Motivazione |
| --- | --- | --- |
| data_db.py:854 SQL concat | FALSO POSITIVO | La f-string interpola solo placeholder `?` (`','.join(['?']*n)`); tutti i valori passano in `params_hist` a `execute()`. Pattern sicuro standard per clausole IN |
| AnalyticsPanel.jsx:556 .reverse() | FALSO POSITIVO | `[...sessions].reverse()`: lo spread crea una copia prima del reverse, lo stato React non viene mutato. Idioma corretto; eventuale `toReversed()` solo cosmetico |
| config.py:536 SSRF pattern | BY DESIGN, accettabile | `test_camera_stream` costruisce RTSP da input operatore perche`e` la sua funzione (test camera con IP parametrico). Chiamante = solo operatore via LAN/Tailnet; log senza credenziali. Rafforzamento futuro opzionale: validare formato IP |

### C. Robustezza (ast-grep)

- `config_loader.py`: 7 chiamate lancianti senza try/except (linee 71, 72, 143, 177, 188, 200, 201). Un `config.json` malformato sul PC a deploy tempo = backend giu con traceback grezzo. Candidato a guard con messaggio d'errore pulito. **Resta APERTO (backlog item 6).**
- **Regola `unchecked-throwing-call-python` disattivata a livello progetto** (`.pi-lens.json`, 2026-09-11): genera ~40 finding baseline quasi tutti su `int()`/`float()` nei hot loop di inferenza YOLO (valori numerici, mai non-numerici in pratica). I pattern veramente utili della regola (`open()`/`json.loads`) sono gia` tracciati in backlog item 6; riesaminare la disattivazione quando item 6 lands.

---

## Frontend - 0 errori, 109 warning (qualita, non bug)

Distribuzione per categoria:

| Categoria | Conteggio | File principali |
| --- | --- | --- |
| console.log/debug in produzione | ~35 | App.jsx (28), VideoFeedPanel (5), GateEditor (7), SettingsModal (2) |
| ternari annidati | ~22 | AnalyticsPanel (6), SpeedTableViewer (7), ConsistController (4), altri |
| alert() | 11 | SettingsModal (6), ConsistManagerModal (4), SpeedTableViewer (1), AnalyticsPanel (1) |
| isNaN/isFinite globali | 8 | SpeedTableViewer (6), DeltaTChart (2), AnalyticsPanel (2) |
| == invece di === | 3 | AnalyticsPanel (2), HistoricalTrendChart (1) |
| .reverse() mutante | 1 | AnalyticsPanel:556 |
| .filter().length invece di .some() | 1 | ConsistManagerModal:220 |
| JSON.parse(JSON.stringify()) | 2 | SettingsModal:69,137 |
| webkitAudioContext (hint TS) | 1 | App.jsx:106 |

**Segnali da non perdere**:

- `AnalyticsPanel.jsx:556` - `.reverse()` su array che potrebbe essere stato React: potenziale bug sottile (mutazione di stato), non solo stile
- `alert()` in conflitto con il sistema di notifiche esistente (`useNotification.jsx`) - refactoring meccanico a basso costo

**Hint TS utili**: AnalyticsPanel ha 6 import/variabili inutilizzate (memo, filterEventsBySession, getAddressFilter, formatOperatingTime, getSpeedTuningRecommendation, formatDuration) - pulizia immediata.

---

## Vista strutturale (review graph, 77/77 file)

### Hub ad alto fan-in (modifiche ad impatto largo)

| File | Importer | Blast radius |
| --- | --- | --- |
| backend/log_colors.py | 17 | 26 |
| backend/config_loader.py | 15 | 22 |
| backend/z21_manager.py | 9 | 22 |
| web/src/utils/analyticsHelpers.js | 6 | 26 |
| backend/services/data_db.py | 6 | 14 |

### Risk hotspots (complessita cicomatica)

| Componente | Complessita | Righe |
| --- | --- | --- |
| components/AnalyticsPanel.jsx | 203 | 1280+ |
| App.jsx | 185 | 1416 |
| components/charts/SpeedTableViewer.jsx | 182 | 1030+ |
| components/ConsistController.jsx | 115 | - |

Coerenti con `docs/FRONTEND_REFACTOR_PLAN.md` (AnalyticsPanel era 1684 righe al tempo del piano).

### Cicli e layering

- Ciclo largo: backend <-> routers <-> services <-> tracking <-> websocket_handlers (79 archi). In parte intrinseco ai router FastAPI; quantificare con /lens-tdi prima di decidere interventi.
- 4 layering violations minori (services -> backend, main -> routers, ecc.).
- `main.py`: lifespan di ~285 righe (175-459) - candidato estrazione. Nota storica: dal refactor era 2340 righe, ora 782 (`docs/REFACTOR_PLAN.md` parzialmente eseguito).
- **Verifica strutturale via lens-map payload (2026-09-11)**: zero import diretti backend<->web (le metà comunicano solo via HTTP/WS); `scripts/z21.py` confermato hub del protocollo (importato da main, routers, WS handlers, tracking - design a stella sano); hub confermati (z21_manager grado 20, log_colors 18, main 18, config_loader 17). Unico falso positivo grafico documentato: `web/src/hooks/useWebSocket.js -> backend/z21_manager.py` (impossibile: JS non importa Python - risoluzione errata di una stringa).

### Dead weight segnalato (bassa confidenza - NON cancellare senza verifica)

Script CLI/one-off con runtime registration: `bump_version.py`, `read_cv_from_roster.py`, script training YOLO, `camera_utils.py`, `migrate_decoder_metadata.py`, `track_consist_yolo.py`. Tutti falsi positivi attesi (chiamati da shell, task scheduler o JMRI sync documentato in AGENTS.md).

**Verificato 2026-09-11 via lens-map payload** (grado 0 in entrata/uscita per tutti): one-off script + build config (eslint/postcss/tailwind/vite) + `__init__.py` vuoti — nessun file vivo orfano, confermati falsi positivi.

---

## Backlog prioritario consolidato

Unico elenco per futuro intervento, in ordine di valore/costo:

1. ~~**Config Pyright sul venv**~~ - RISOLTO 2026-09-11: `pyrightconfig.json` (root, venvPath) + `backend/pyrightconfig.json` (nuovo, venvPath ".."). Baseline CLI: 19 errori -> 15 dopo i fix.
2. ~~**Bug LOW risk baseline** (sez. A.4)~~ - RISOLTO 2026-09-11: 4 fix applicati e verificati col Pyright del venv (yolo_tracker Optional + yolo_obb hoist, tracking_manager set_auto_compensation, speed_table_helpers Optional). Baseline: 15 errori residui = video_feed 6 + downsampling 6 + yolo ultralytics 3.
3. ~~Verifica SQL data_db.py:854~~ - VERIFICATO: falso positivo (B.1), archiviato.
4. ~~**defusedxml in roster_loader.py**~~ - RISOLTO 2026-09-11: import defusedxml + 3 guard `root is None` (aggiunti perche le stub di defusedxml tipizzano getroot() Optional) + `defusedxml==0.7.1` in backend/requirements.txt e venv.
5. ~~`.reverse()` mutante AnalyticsPanel:556~~ - VERIFICATO: falso positivo (B.1), nessun fix.
6. **Guard su config_loader.py** (messaggi d'errore puliti su config malformata).
7. **Pulizia frontend meccanica**: imports inutilizzati AnalyticsPanel, console.log in catch, alert() -> useNotification. (~1-2 h)
8. **video_feed.py + downsampling.py** (MODERATE, ~1-1.5 h, preferibilmente con test).
9. **data_db.py TypedDict + test analytics** (HIGH, ~2-3 h, agganciare a v1.1.0).
10. **Split monoliti frontend** (vedi FRONTEND_REFACTOR_PLAN.md) e estrazione lifespan - da fare dopo /lens-tdi per quantificare.

---

## Cross-reference documentazione esistente

| Documento | Contenuto | Relazione con questo audit |
| --- | --- | --- |
| docs/PYRIGHT_ANALYSIS.md | Audit typing backend v0.9.11 (rimosso 2026-09-11) | Contenuto assorbito in sezione A di questo audit (questo file e`l'unico punto di verita`) |
| docs/REFACTOR_PLAN.md | Modularizzazione backend (main.py 2340 -> attuale) | Parzialmente eseguito; main.py ora 782 righe |
| docs/FRONTEND_REFACTOR_PLAN.md | Modularizzazione AnalyticsPanel | Coerente con hotspot attuali |
| docs/DB_REFACTORING.md | Refactoring DB | Contesto per data_db.py |
| docs/LOG_REFACTORING.md | Refactoring log | Contesto per console.log frontend / log backend |

---

## Come ripetere l'audit

```bash
# Backend: type check ufficiale (gate pre-commit, baseline atteso 12 errori veri:
#   video_feed 6 + downsampling 6, deferiti; i venv config hanno eliminato il rumore)
pyright backend/

# Frontend + backend con pi-lens (sessione agent): scansione full warning
#   lens_diagnostics source=lsp scope=workspace mode=full path=web/src
#   lens_diagnostics source=lsp scope=workspace mode=full path=backend
#   severity=warning per includere gli errori

# Vista strutturale
#   project_report (hubs, cicli, hotspots, dead weight)
```

## Esito review post-fix (2026-09-11, subagent glm-5.3 thinking high)

Review READ-ONLY su 54a09f7 + 63aa397: **nessun P1**. Verifica empirica del reviewer: baseline pyright 12 errori esatti sia da root sia da backend/ (config coerenti).

- **P2.1 (operativo, prima del deploy PC)**: defusedxml deve essere installato nel venv del PC PRIMA del restart, altrimenti il backend non parte (roster_loader lo importa a livello modulo; gli alias di deploy non fanno pip install). Comando: `ssh riccardo@gaming-pc "cd C:\z21-Terminal && .\venv\Scripts\python.exe -m pip install -r backend\requirements.txt"` poi `z21-restart`. Valutare in futuro un check requirements negli alias di deploy.
- **P3.2 guard `root is None`**: DECISIONE = mantenuti come defense-in-depth. Il reviewer li rileva irraggiungibili (getroot() non ritorna None dopo parse riuscito), ma rimuoverli reintrodurrebbe i pyright errori da stub Optional di defusedxml. Inoffensivi e documentati.
- **P3.3 `cast(Any, ...)`**: DECISIONE = mantenuto per ora. Alternativa futura piu` tipizzata: `cast(List["Results"], ...)` con import lazy di ultralytics.engine.results; da valutare se le stub migliorano. Nota INFO correlata: le due pyrightconfig (root + backend) vanno tenute sincronizzate a mano (rischio drift).
- Tutti gli altri punti verificati OK (hoist yolo_obb semanticamente equivalente e NameError reale confermato con call site vivo in scripts/track_consist_yolo.py:692; set_auto_compensation firma e semantica corrette; guard roster_loader non alterano il flusso; config valide su Mac e PC).

## Baseline TDI project-wide (2026-09-11, dopo full sweep)

Prima misurazione su tutto il progetto. Metodo: sweep manuale con `read limit=5` su tutti gli 80 file git-tracked (.py/.js/.jsx) — ogni lettura scatta la complexity baseline di pi-lens (tree-sitter, analisi dal disco) e cattura lo snapshot in `~/.pi-lens/projects/<slug>/metrics-history.json`. In `~/.pi-lens/projects/Users-riccardosallusti-Documents-PROGETTI-z21-Terminal/metrics-history.json`. Per aggiornare la fotografia: ripetere la sweep (i file gia` presenti prendono un nuovo snapshot e aggiornano il trend).

```text
TECHNICAL DEBT INDEX: 37.1/100 (C - debito moderato)
Files analyzed: 80 | Files with debt: 66 | Avg MI: 59.7 | Total cognitive: 8901
Breakdown: Maintainability 40% | Cognitive 34% | Nesting 27% | Max Cyclomatic 29% | Entropy 62%
```

Scala: punteggio ALTO = piu` debito. Il campione di 6 file caldi di stamattina segnava 59 (D): il progetto intero sta meglio del suo campione caldo, come doveva essere.

File peggiori per MI (il debito e` concentrato, ~15-20% del totale vive in 6-7 file):

| File | MI | Cognitiva | Righe |
| --- | --- | --- | --- |
| web/src/components/SettingsModal.jsx | 35.5 | 224 | 1.244 |
| web/src/components/AnalyticsPanel.jsx | 38.5 | 463 | 1.143 |
| backend/services/data_db.py | 40.0 | 310 | 841 |
| web/src/App.jsx | 40.9 | 677 | 1.156 |
| web/src/components/charts/SpeedTableViewer.jsx | 42.5 | 429 | 949 |
| web/src/components/ConsistController.jsx | 43.8 | 281 | 594 |
| scripts/z21_controller.py (CLI) | 44.9 | 706 | 818 |
| backend/routers/config.py | 45.3 | 410 | 671 |
| web/src/components/ConsistForm.jsx | 46.2 | 98 | 405 |
| backend/routers/speed_table.py | 46.6 | 187 | 524 |
| scripts/track_consist_yolo.py | 47.0 | 476 | 710 |
| backend/main.py | 47.1 | 379 | 585 |

Note di lettura:
- **Entropy 62%** e` il peso dominante a livello progetto (imprevedibilita`/mischia di pattern), la complessita` cognitiva e` concentrata in pochi file, non diffusa
- Novita` rispetto ai radar precedenti: **SettingsModal.jsx** (MI peggiore del progetto) e **z21_controller.py** (CLI, cognitiva 706) emergono solo con la sweep completa
- I file con metriche nulle sono i 3 `__init__.py` vuoti (corretto)
- Da qui in poi i refactor mostreranno `improving/regressing` per file in `/lens-tdi` (confronto tra snapshot storici)

Ultimo aggiornamento: 2026-09-11, audit generato da pi-lens su develop.
