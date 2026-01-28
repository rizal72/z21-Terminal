# Memory Testing Suite - z21-Terminal

Suite completa per il testing dell'uso della memoria di z21-Terminal, pensata per valutare il deployment su Jetson Orin Nano.

## 🎯 Obiettivo

Determinare i requisiti minimi di RAM e VRAM per eseguire z21-Terminal su:
- **Jetson Orin Nano** (8GB RAM) - Target deployment
- Confronto con **MacBook Pro** (16GB RAM) - Ambiente sviluppo attuale

## 📦 Componenti Monitorati

### 1. Backend Python (FastAPI + YOLO)

**Processi**:
- `backend/main.py` - FastAPI server
- `tracking_daemon.py` - YOLO tracking daemon (se attivo)

**Metriche**:
- RSS (Resident Set Size) - RAM fisica utilizzata
- VMS (Virtual Memory Size) - Memoria virtuale totale
- %RAM - Percentuale della RAM totale utilizzata
- CPU% - Utilizzo CPU
- Thread count - Numero di thread attivi

**Script**: `backend_memory_monitor.py`

### 2. Frontend React (Browser)

**Metriche**:
- JavaScript Heap Size - Memoria heap utilizzata dal browser
- DOM Node Count - Numero di nodi nel DOM
- React Component Count - Numero di componenti React montati
- WebSocket Traffic - Dimensione messaggi scambiati

**Strumenti**:
- `frontend_memory_test.js` - Snippet JavaScript per Chrome DevTools MCP
- `memory_test.html` - Dashboard per test manuali

### 3. YOLO Model (GPU/CPU)

**Metriche**:
- VRAM utilizzata (se TensorRT attivo)
- RAM per model weights (PyTorch/ONNX)
- Inference time per frame

**Note**: Richiede TensorRT GPU per misurazioni VRAM accurate

## 🚀 Guida Rapida

### Test Completo Automatico

**IMPORTANTE**: I test vanno eseguiti sul **PC server (gaming-pc)** via SSH, NON sul Mac.

```bash
# SUL MAC (sviluppo)
# 1. Commit e push i test su GitHub
git add .
git commit -m "test: aggiorna memory test suite"
git push origin develop

# SUL PC (server) via SSH
# 2. Pull le modifiche
ssh riccardo@gaming-pc "cd C:/z21-Terminal && git pull"

# 3. Verifica che z21-Terminal sia in esecuzione
ssh riccardo@gaming-pc "z21-status"

# 4. Se non running, avvialo
ssh riccardo@gaming-pc "z21-start"

# 5. Esegui test memoria completo (10 minuti)
ssh riccardo@gaming-pc "cd C:/z21-Terminal/test/memory && ./run_full_memory_test.sh --duration 10"

# 6. Analizza i risultati (dal PC)
ssh riccardo@gaming-pc "cat C:/z21-Terminal/test/memory/results/backend_memory_*.csv"
ssh riccardo@gaming-pc "cat C:/z21-Terminal/test/memory/results/summary_report_*.md"
```

### Test Manuale Frontend (Chrome DevTools MCP)

```bash
# 1. Apri la dashboard in Chrome
open http://localhost:5173

# 2. Apri il test dashboard HTML in un'altra tab
open test/memory/results/memory_test.html

# 3. In Claude Code, usa Chrome DevTools MCP:
#    - Esegui snippet da frontend_memory_test.js
#    - Prendi snapshot memoria heap
#    - Analizza WebSocket traffic
```

## 📊 Analisi Risultati

### Backend (CSV)

Il file CSV generato contiene colonne:

| Colonna | Descrizione |
|---------|-------------|
| `timestamp` | ISO timestamp della misurazione |
| `rss_mb` | RAM fisica utilizzata (MB) |
| `vms_mb` | Memoria virtuale (MB) |
| `percent` | % della RAM totale |
| `num_threads` | Numero di thread attivi |
| `cpu_percent` | Utilizzo CPU (%) |

**Esempio analisi**:

```bash
# Statistiche RAM min/max/media
awk -F, 'NR>1 {sum+=$2; count++} END {print "Avg RAM:", sum/count " MB"}' results/backend_memory_*.csv

# Trova picco massimo RAM
awk -F, 'NR>1 && $2>max {max=$2} END {print "Max RAM:", max " MB"}' results/backend_memory_*.csv
```

### Frontend (Snapshots)

I snapshot JavaScript sono salvati in `window.__memory_snapshots__` e includono:

```json
{
  "label": "baseline",
  "timestamp": "2026-01-28T10:30:00",
  "used_mb": "45.23",
  "percent": "0.45"
}
```

**Thresholds consigliati**:
- **Idle**: < 50 MB heap
- **Active**: < 100 MB heap
- **Leak warning**: > 10% growth tra snapshot

## 🔬 Scenari di Test

### 1. Idle (App avviata, nessun tracking)

**Condizioni**:
- Backend running, nessun WebSocket connesso
- Frontend caricato, nessuna interazione
- YOLO daemon non attivo

**Atteso**:
- Backend: ~150-250 MB RAM (Python + FastAPI)
- Frontend: ~30-50 MB heap
- Totale: < 300 MB

### 2. Active (Dashboard aperta, tracking attivo)

**Condizioni**:
- 1+ WebSocket connessi
- YOLO tracking running (30 FPS)
- Analytics chart con dati

**Atteso**:
- Backend: ~500-800 MB RAM (YOLO model loaded)
- Frontend: ~50-80 MB heap
- VRAM: ~500 MB (TensorRT OBB model)

### 3. Peak (Tutto al massimo carico)

**Condizioni**:
- 3+ WebSocket connections (multi-device)
- YOLO tracking 30 FPS + video feed
- Analytics chart con 500+ events

**Atteso**:
- Backend: ~1-1.5 GB RAM
- Frontend: ~80-120 MB heap
- VRAM: ~600-800 MB

## 📈 Requisiti Jetson Orin Nano

### Stima Preliminare (da confermare con test)

Basato su stack tecnologico:

| Componente | RAM Stimata | VRAM Stimata |
|------------|-------------|--------------|
| Ubuntu 20.04 (base) | ~500 MB | - |
| Python runtime | ~50 MB | - |
| FastAPI + WebSocket | ~100 MB | - |
| YOLOv8 OBB (PyTorch) | ~400 MB | ~600 MB |
| Database SQLite | ~10 MB | - |
| Video Feed (MJPEG) | ~50 MB | - |
| **TOTALE** | **~1.1 GB** | **~600 MB** |

**Margini**:
- Buffer sistema: +500 MB
- Picchi temporanei: +300 MB

**Raccomandazione**:
- **RAM minima**: 2 GB (consigliati 4 GB per stabilità)
- **VRAM minima**: 1 GB (TensorRT OBB model)

### Jetson Orin Nano (8GB)

**Verdetto**: ✅ **Più che adeguato**

L'Orin Nano da 8GB ha margine più che sufficiente per:
- Sistema operativo + applicazioni
- YOLO tracking con TensorRT
- Multi-device WebSocket connections
- Future espansioni (e.g., TensorRT per altri modelli)

## 🔧 Troubleshooting

### psutil non installato

```bash
pip install psutil
```

### Chrome DevTools MCP non connette

```bash
# Verifica che il server MCP sia in esecuzione
# Vedi: docs/CHROME_DEVTOOLS_OPTIMIZATION.md
```

### Backend crash durante test

```bash
# Controlla log
tail -f backend/z21-terminal.log

# Riduci intervallo sampling
./run_full_memory_test.sh --interval 10  # 10 secondi invece di 5
```

## 📝 Prossimi Passi

1. **Esegui test complete** su Mac (ambiente attuale)
2. **Analizza risultati** e conferma stime
3. **Crea ambiente Jetson** e ripeti test
4. **Confronta** Mac vs Jetson performance
5. **Crea** `docs/JETSON_DEPLOYMENT.md` con guida completa setup

## 🔗 Risorse Correlate

- [Chrome DevTools Optimization](../../docs/CHROME_DEVTOOLS_OPTIMIZATION.md)
- [Computer Vision - TensorRT](../../docs/TENSORRT_OPTIMIZATION.md)
- [Backend Architecture](../../docs/REFACTOR_PLAN.md)
