# Jetson Orin Nano Deployment - z21-Terminal

**Version**: 1.0.0
**Last Updated**: 2026-01-28
**Purpose**: Deploy z21-Terminal come Docker container standalone su NVIDIA Jetson Orin Nano

---

## 🎯 Overview

Questa guida spiega come distribuire z21-Terminal su **NVIDIA Jetson Orin Nano** tramite Docker container. L'obiettivo è creare un ambiente **standalone, ottimizzato e riproducibile** che possa girare ovunque.

### Perché Docker?

| Vantaggio | Descrizione |
|-----------|-------------|
| **Portabilità** | Run ovunque (Linux, Mac, Jetson) senza setup manuale |
| **Ottimizzazione CUDA** | PyTorch + TensorRT già configurati nell'immagine L4T |
| **Isolamento** | Zero conflitti con altre applicazioni |
| **Aggiornamenti** | Rollback facile, deploy automatici |

### Stack Tecnologico

```
┌─────────────────────────────────────────────────┐
│         Docker Container (Jetson)                │
├─────────────────────────────────────────────────┤
│  React Frontend (Vite + Tailwind CSS)            │
│  FastAPI Backend + WebSocket                     │
│  YOLO Tracking (Ultralytics + TensorRT)          │
│  PyTorch + CUDA + cuDNN (da L4T image)           │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│     NVIDIA Jetson Orin Nano (8GB RAM)           │
│     - Ubuntu 20.04 LTS (JetPack 5.1+)            │
│     - GPU Ampere 1024 cores                      │
│     - TensorRT 8.5                               │
└─────────────────────────────────────────────────┘
```

---

## 📋 Prerequisiti Hardware

### Jetson Orin Nano Raccomandato

| Modello | RAM | YOLO FPS | Verdetto |
|---------|-----|----------|----------|
| **8GB** | 8 GB | 60-90 | ✅ **Raccomandato** |
| **4GB** | 4 GB | 50-70 | ⚠️ Margini ridotti |

### Altri Componenti

- **Scheda microSD**: 32GB+ (Class 10) o NVMe SSD
- **Alimentatore**: NVIDIA originale (necessario per MAX performance)
- **Rete**: WiFi o Ethernet (per Z21 communication)
- **Camera**: IP camera RTSP (es. Tapo C100)

---

## 🚀 Quick Start (3 Step)

### Step 1: Valutazione Risorse 📊

Prima di deployare, valuta se il Jetson ha risorse sufficienti.

```bash
# SUL MAC
git add .
git commit -m "docs: aggiungi guide deployment Jetson"
git push origin develop

# SUL PC (via SSH)
ssh riccardo@gaming-pc "cd C:/z21-Terminal && git pull"
ssh riccardo@gaming-pc "cd C:/z21-Terminal/test/memory && ./run_full_memory_test.sh --duration 10"

# Analizza risultati
ssh riccardo@gaming-pc "cat C:/z21-Terminal/test/memory/results/summary_report_*.md"
```

**Risultato atteso** (per Jetson 8GB):
- Backend RAM: ~1.5 GB
- VRAM TensorRT: ~1 GB
- **Totale**: < 3 GB (✅ Sufficente)

> **Documentazione completa**: [test/memory/README_MEMORY.md](../test/memory/README_MEMORY.md)

---

### Step 2: Build Docker Image 🐳

```bash
# SUL MAC
# 1. Commit e push codice
git add .
git commit -m "feat: prepara deployment Jetson"
git push origin develop

# SUL JETSON (via SSH)
# 2. Clone repository (prima volta solo)
ssh jetson@jetson-orin-nano
git clone git@github.com:rizal72/z21-Terminal.git
cd z21-terminal
git checkout develop

# 3. Configurazione
cp config.local.json.example config.local.json
nano config.local.json  # Inserisci credenziali camera RTSP

# 4. Build Docker image
docker build -f test/docker/Dockerfile.jetson -t z21-terminal:jetson .
```

**Tempo di build**: ~10-15 minuti

> **Documentazione Docker dettagliata**: [test/docker/README_JETSON_DOCKER.md](../test/docker/README_JETSON_DOCKER.md)

---

### Step 3: Deploy & Run ▶️

```bash
# SUL JETSON
# 1. Avvia container con Docker Compose
docker-compose -f test/docker/docker-compose.jetson.yml up -d

# 2. Controlla log
docker-compose -f test/docker/docker-compose.jetson.yml logs -f

# 3. Verifica health
curl http://localhost:8000/api/status

# 4. Apri dashboard
# Dal Jetson: http://localhost:8000
# Da altro device: http://<JETSON_IP>:8000
```

✅ **Fatto!** z21-Terminal è ora in esecuzione sul Jetson.

---

## 📊 Architettura Docker

### Immagine Base: NVIDIA L4T-PyTorch

```dockerfile
FROM nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.1-py3
```

**Include già**:
- ✅ Python 3.10
- ✅ PyTorch 2.1 (ARM64 + GPU)
- ✅ CUDA 11.4
- ✅ cuDNN 8.6
- ✅ TensorRT 8.5

**NON安装** (perché già presente):
- ❌ PyTorch (già nell'immagine L4T)
- ❌ CUDA toolkit (già configurato)
- ❌ TensorRT (già incluso)

### Cosa Fa il Dockerfile

Il Dockerfile **NON ricrea da zero** z21-Terminal. Si limita a:

1. Installare **Node.js** (per frontend build)
2. Installare **Python deps** dai requirements.txt esistenti:
   - `backend/requirements.txt` (FastAPI, uvicorn, websockets)
   - `scripts/requirements.txt` (ultralytics, opencv)
3. **Copiare codice esistente** (backend, scripts, web, config)
4. **Build frontend** (React + Vite + Tailwind CSS)
5. **Copiare YOLO models** (.engine, .onnx, .pt)

### Priorità Modelli YOLO

z21-Terminal usa i modelli in questo ordine:

1. **best_obb.engine** (TensorRT) - PRIMARIO, compilato per GPU specifica
2. **best_obb.onnx** (ONNX) - Fallback se .engine non disponibile
3. **best_obb.pt** (PyTorch) - Fallback finale per export

Se `.engine` NON è presente per la GPU del Jetson:
- yolo_tracker.py lo compilerà automaticamente al primo avvio
- Tempo di compilazione: ~5-10 minuti (solo prima volta)
- Il file persiste in `scripts/models/`

---

## ⚙️ Ottimizzazioni Jetson

### 1. Power Mode (NVP Model)

Il container imposta automaticamente la modalità **MAX performance**:

```bash
# In docker-entrypoint.sh
sudo nvpmodel -m 0  # MAX performance mode (15W-20W)
sudo jetson_clocks  # Massimizza CPU/GPU/EMC clocks
```

### 2. Swap File

Raccomandato aggiungere swap per evitare OOM:

```bash
# Crea 4GB swap file
sudo fallocate -l 4G /mnt/4GB.swap
sudo chmod 600 /mnt/4GB.swap
sudo mkswap /mnt/4GB.swap
sudo swapon /mnt/4GB.swap

# Rendi permanente
echo '/mnt/4GB.swap none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Network Mode

Usa `network_mode: host` per Z21 UDP communication:

```yaml
# In docker-compose.jetson.yml
network_mode: host  # Necessario per Z21 UDP broadcast
```

---

## 📈 Performance Attese

| Configurazione | YOLO FPS | RAM Usage | VRAM Usage | Note |
|----------------|----------|-----------|------------|------|
| Jetson Orin Nano 8GB (MAX performance) | 60-90 | ~1.5 GB | ~1 GB | ✅ Raccomandato |
| Jetson Orin Nano 4GB (MAX performance) | 50-70 | ~2.5 GB | ~1 GB | ⚠️ Margini ridotti |
| Jetson Orin Nano 8GB (15W mode) | 40-60 | ~1.2 GB | ~800 MB | ✅ Buon compromise |

### Requisiti Minimi

Basato su test memoria effettuati su PC Windows:

| Componente | Min RAM | Max RAM | Note |
|------------|---------|---------|------|
| Ubuntu 20.04 (base) | 500 MB | 800 MB | |
| Python runtime | 50 MB | 100 MB | |
| FastAPI + WebSocket | 100 MB | 200 MB | |
| YOLOv8 OBB (TensorRT) | 400 MB | 600 MB | |
| SQLite database | 10 MB | 50 MB | |
| MJPEG video feed | 50 MB | 100 MB | |
| System buffer | 500 MB | 1000 MB | |
| **TOTAL (Min)** | **1.6 GB** | **2.8 GB** | |
| **TOTAL (Recommended)** | **2.5 GB** | **4 GB** | |

**Verdetto Jetson Orin Nano 8GB**: ✅ **Più che adeguato** (5.2 GB margin)

---

## 🔧 Troubleshooting

### Container non parte

```bash
# Controlla log
docker logs z21-terminal-jetson

# Verifica GPU accessibile
docker run --rm --gpus all nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.1-py3 nvidia-smi
```

### Out of Memory (OOM)

```bash
# Controlla RAM libera
free -h

# Controlla swap
swapon --show

# Aumenta swap (vedi sezione 2 sopra)
```

### YOLO lento sulla CPU

```bash
# Verifica che TensorRT stia usando GPU
docker exec z21-terminal-jetson nvidia-smi

# Controlla log per errori TensorRT
docker logs z21-terminal-jetson | grep -i tensorrt

# Verifica che .engine sia stato generato
docker exec z21-terminal-jetson ls -lah /app/scripts/models/
```

### Frontend non si carica

```bash
# Verifica che il build sia andato a buon fine
docker exec z21-terminal-jetson ls -lah /app/web/dist/

# Se non presente, ricostruisci immagine
docker-compose -f test/docker/docker-compose.jetson.yml build --no-cache
```

### Z21 Non Raggiungibile

```bash
# Verifica network mode (deve essere "host")
docker inspect z21-terminal-jetson | grep NetworkMode

# Verifica che Z21 sia raggiungibile dal Jetson
ping 192.168.1.111

# Test UDP communication
nc -u -z 192.168.1.111 21105
```

---

## 🔄 Aggiornamento Container

```bash
# SUL MAC (sviluppo)
# 1. Commit e push modifiche
git add .
git commit -m "feat: aggiornamento codice"
git push origin develop

# SUL JETSON via SSH
# 2. Pull ultime modifiche
ssh jetson@jetson-orin-nano "cd /home/jetson/z21-terminal && git pull"

# 3. Ricostruisci e riavvia container
ssh jetson@jetson-orin-nano "cd /home/jetson/z21-terminal && docker-compose -f test/docker/docker-compose.jetson.yml down"
ssh jetson@jetson-orin-nano "cd /home/jetson/z21-terminal && docker-compose -f test/docker/docker-compose.jetson.yml build --no-cache"
ssh jetson@jetson-orin-nano "cd /home/jetson/z21-terminal && docker-compose -f test/docker/docker-compose.jetson.yml up -d"
```

---

## 🔒 Sicurezza

### Non montare config.local.json in scrittura

```yaml
# In docker-compose.jetson.yml
volumes:
  - ./config.local.json:/app/config.local.json:ro  # Read-only!
```

### Limita risorse se necessario (4GB model)

```yaml
deploy:
  resources:
    limits:
      memory: 3.5G
```

### Volume persistente per database

```yaml
volumes:
  z21-data:  # Database SQLite persiste
```

---

## 📚 Documentazione Correlata

### Deployment
- **[Docker Jetson Dettagliato](../test/docker/README_JETSON_DOCKER.md)** - Dockerfile, docker-compose, troubleshooting
- **[Test Suite](../test/README.md)** - Testing memoria e performance

### Computer Vision
- **[TensorRT Optimization](./TENSORRT_OPTIMIZATION.md)** - TensorRT export workflow
- **[Computer Vision](./COMPUTER_VISION.md)** - YOLO training e tuning
- **[YOLO Model Priority](../test/docker/README_JETSON_DOCKER.md#2-tensorrt-engine)** - .engine → .onnx → .pt

### Altro
- **[Chrome DevTools Optimization](./CHROME_DEVTOOLS_OPTIMIZATION.md)** - MCP server per testing frontend
- **[Backend Architecture](./REFACTOR_PLAN.md)** - Modular architecture design

---

## 🔗 Risorse Esterne

- [NVIDIA NGC L4T PyTorch](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch)
- [Jetson Orin Nano Technical Overview](https://developer.nvidia.com/embedded/jetson-orin-nano)
- [TensorRT Documentation](https://docs.nvidia.com/deeplearning/tensorrt/)
- [Docker on Jetson](https://developer.nvidia.com/embedded/learn/tutorials/v/sensor-docker-camera)

---

## ⚠️ Note Importanti

1. **PyTorch è già incluso** nell'immagine L4T - NON reinstallarlo
2. **Il TensorRT .engine** è specifico per ogni GPU - viene generato sul Jetson
3. **Usa `git add .`** sempre - non specificare percorsi singoli
4. **Network mode host** è necessario per Z21 UDP broadcast
5. **Power mode MAX** è raccomandato per performance YOLO ottimali
6. **Memory testing** è uno strumento di valutazione, non l'obiettivo finale
