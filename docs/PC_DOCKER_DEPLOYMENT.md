# PC Docker Deployment - z21-Terminal

**Version**: 1.0.0
**Last Updated**: 2026-01-28
**Purpose:** Dockerizzare z21-Terminal per PC Windows/Linux con supporto GPU opzionale e Tailscale HTTPS

---

## 🎯 Overview

Dockerizzare z21-Terminal per creare un container **standalone e portatile** che possa girare su qualsiasi PC, con o senza GPU, mantenendo l'accesso Tailscale HTTPS configurato.

### Obiettivi

- ✅ **Portatile**: Run su qualsiasi PC Windows/Linux senza setup manuale
- ✅ **Isolamento**: Non sporca il filesystem, facile cleanup
- ✅ **GPU Opzionale**: Con CUDA veloce, senza funziona comunque (YOLO fallbacks)
- ✅ **Tailscale HTTPS**: Accessibile via `https://gaming-pc.tail9350d7.ts.net` senza specificare porta
- ✅ **Liberà il PC**: Container può runnare in background, PC libero per altri task
- ✅ **Distribuzione Pubblica**: Container standalone condivisibile via Docker Hub

---

## 🌐 Docker Distribution Strategy

### Visione: Container Standalone per Distribuzione

**Obiettivo a lungo termine**: Creare un container Docker completamente autonomo che contenga TUTTO z21-Terminal, distribuibile a chiunque abbia solo Docker installato.

```
┌─────────────────────────────────────────────────┐
│  Repository GitHub (Privato)                    │
│  └─ rizal72/z21-Terminal                        │
│     └─ Codice sorgente completo                 │
│        ├─ backend/                              │
│        ├─ web/                                  │
│        ├─ scripts/                              │
│        └─ docs/                                 │
└─────────────────────────────────────────────────┘
                    │ docker build + push
                    ▼
┌─────────────────────────────────────────────────┐
│  Docker Hub (Pubblico)                          │
│  └─ rizal72/z21-terminal                        │
│     ├─ latest                                   │
│     ├─ v1.0.0                                   │
│     └─ v1.1.0                                   │
└─────────────────────────────────────────────────┘
                    │ docker pull + run
                    ▼
┌─────────────────────────────────────────────────┐
│  PC dell'utente (qualsiasi OS)                  │
│  ├─ Docker Desktop installato                   │
│  └─ Container z21-Terminal (tutto incluso)      │
│      ├─ Backend Python + FastAPI                │
│      ├─ Frontend React (dist/)                  │
│      ├─ YOLO models (.engine, .onnx, .pt)       │
│      ├─ Configurazioni default                  │
│      └─ Database SQLite (creato al primo run)   │
└─────────────────────────────────────────────────┘
```

### Repository Strategy

| Componente | Visibility | Location | Access |
|------------|------------|----------|--------|
| **Codice sorgente** | 🔒 Privato | GitHub - rizal72/z21-Terminal | Solo sviluppatori |
| **Container Docker** | 🌍 Pubblico | Docker Hub - rizal72/z21-terminal | Chiunque |

**Perché questa strategia?**

✅ **Codice privato**: Proteggi IP, configurazioni personali, documentazione interna
✅ **Container pubblico**: Chiunque può usare z21-Terminal senza vedere il codice
✅ **Facile aggiornamento**: `docker pull rizal72/z21-terminal:latest`
✅ **Versioning semantico**: Tag specifici per stabilità (v1.0.0, v1.1.0, ecc.)

### Cosa include il Container Standalone

Il container Docker include **TUTTO** necessario per funzionare:

```
z21-terminal-container (~1.5-2GB)
├── Python 3.10 runtime
├── FastAPI + WebSocket
├── OpenCV, NumPy, Ultralytics YOLO
├── Frontend React (HTML/CSS/JS già buildato)
├── YOLO models (.engine per GPU, .onnx/.pt fallback)
├── Configurazioni default (config.json)
└── Database SQLite (creato vuoto al primo run)
```

**Cosa NON serve sull'host**:
- ❌ Python
- ❌ Node.js
- ❌ venv
- ❌ npm/node_modules
- ❌ YOLO models
- ❌ Codice sorgente

**Solo Docker Desktop** = Tutto il resto è nel container!

### Workflow di Distribuzione

#### 1. **Sviluppo** (Mac/PC locale)
```bash
# Sviluppo normale
git checkout develop
# ... modifica codice ...
git add .
git commit -m "feat: nuova feature"
git push origin develop
```

#### 2. **Build Container** (Mac)
```bash
# Dalla radice del repo
docker build -f test/docker/Dockerfile.pc -t rizal72/z21-terminal:v1.0.0 .

# Test locale
docker run --rm -p 8000:8000 rizal72/z21-terminal:v1.0.0
curl http://localhost:8000/api/status
```

#### 3. **Push su Docker Hub** (Mac)
```bash
# Login (prima volta)
docker login

# Push versionato
docker push rizal72/z21-terminal:v1.0.0

# Push latest (stabile)
docker tag rizal72/z21-terminal:v1.0.0 rizal72/z21-terminal:latest
docker push rizal72/z21-terminal:latest
```

#### 4. **Deploy Utente** (Qualsiasi PC)
```bash
# Utente installa Docker Desktop (una tantum)

# Poi UN SOLO comando:
docker run -d \
  --name z21-terminal \
  -p 8000:8000 \
  -v z21-data:/app/backend/data \
  --restart unless-stopped \
  rizal72/z21-terminal:latest

# Finito! App funziona su http://localhost:8000
```

### Versioning Strategy

**Tag Docker Hub**:
```bash
latest          # Versione stabile più recente
v1.0.0          # Release major (features importanti)
v1.0.1          # Release patch (bugfix)
v1.1.0          # Release minor (nuove features backward compat)
develop         # Build da branch develop (testing)
```

**Quando taggare**:
- `vX.Y.Z` → Quando mergi `develop` → `main` (release stabile)
- `latest` → Aggiornato solo con tag stabili (NON develop)
- `develop` → Build automatica da CI/CD per testing

### Aggiornamento per l'Utente Finale

```bash
# Utente controlla aggiornamenti
docker pull rizal72/z21-terminal:latest

# Se disponibile nuova versione
docker stop z21-terminal
docker rm z21-terminal
docker run -d \
  --name z21-terminal \
  -p 8000:8000 \
  -v z21-data:/app/backend/data \
  --restart unless-stopped \
  rizal72/z21-terminal:latest

# Oppure con docker-compose (più semplice)
docker-compose pull
docker-compose up -d
```

### Differenza: Development vs Production

| Aspect | Development (con volumi) | Production (standalone) |
|--------|-------------------------|-------------------------|
| **Codice dove sta** | Host (mount volume) | Dentro container |
| **Modifiche** | Live reload (no rebuild) | Serve rebuild |
| **Config** | Dal host | Dentro container |
| **Target** | Sviluppo/test | Distribuzione |
| **Git workflow** | `git pull` diretto | `docker pull` |
| **Aggiornamenti** | Facili e veloci | Più lenti ma robusti |

Per z21-Terminal:
- **Development**: Usa volumi per debug facile
- **Production/Distribuzione**: Container standalone con TUTTO dentro

### Vantaggi della Distribuzione Container

| Vantaggio | Descrizione |
|-----------|-------------|
| **Zero install** | Solo Docker, niente Python/node/venv |
| **Zero config** | Config preimpostato, funziona subito |
| **Portabilità** | Windows, Mac, Linux - stessa immagine |
| **Isolamento** | Non inquina il sistema host |
| **Aggiornamenti** | `docker pull` one-command |
| **Rollback** | `docker pull v1.0.0` se problemi |
| **Distribuzione** | Docker Hub pubblico o privato |
| **Documentazione** | README Docker Hub con istruzioni |

### Stack Tecnologico

```
┌─────────────────────────────────────────────────┐
│         Docker Container (PC)                    │
├─────────────────────────────────────────────────┤
│  React Frontend (Vite + Tailwind CSS)            │
│  FastAPI Backend + WebSocket                     │
│  YOLO Tracking (Ultralytics + TensorRT/ONNX/PT)  │
│  Python 3.10 + dipendenze                        │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│     Docker Engine (Windows/Linux)               │
│     - GPU Support (opzionale via nvidia-docker) │
│     - Network bridge (porta 8000)                │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│     Tailscale (Host)                            │
│     - HTTPS Funnel (443 → localhost:8000)        │
│     - Accessibile publicamente                   │
└─────────────────────────────────────────────────┘
```

---

## 📋 Requisiti

### Hardware

| Componente | Minimo | Raccomandato | Note |
|------------|--------|--------------|------|
| **RAM** | 8 GB | 16 GB | Per YOLO tracking |
| **GPU** | CPU only | NVIDIA CUDA 11.8+ | Opzionale, fallback automatico |
| **Storage** | 10 GB free | 20 GB SSD | Per Docker images |
| **Network** | WiFi/Ethernet | Ethernet | Per Tailscale + Z21 UDP |

### Software

#### Richiesti
- **Docker Engine**: 20.10+ ([Install Windows](https://docs.docker.com/desktop/install/windows-install/))
- **Git**: Per clonare il repository
- **Tailscale**: Installato e configurato sul PC host

#### Opzionali ma Raccomandati
- **NVIDIA Docker Runtime**: Per GPU support ([nvidia-docker](https://github.com/NVIDIA/nvidia-docker))
- **Docker Compose**: Per deploy semplificato

### Tailscale Configuration

Il container **NON include Tailscale**. Usa l'host:

1. **Tailscale installato sul PC host**
2. **Tailscale Funnel configurato** per mappare HTTPS (443) → localhost:8000
3. **Container ascolta su 0.0.0.0:8000** (non localhost!)

```bash
# Verifica configurazione Tailscale
tailscale status
tailscale funnel status
```

**Accesso**:
```
https://gaming-pc.tail9350d7.ts.net/     # Automatico, senza porta
```

---

## 🐳 Docker Image Design

### Base Image: `python:3.10-slim`

**Perché questa scelta?**

| Fattore | `python:3.10-slim` | Alternative |
|---------|-------------------|-------------|
| **Size** | ✅ 125 MB | `python:3.10` = 1GB, `alpine` = 50MB |
| **Compatibility** | ✅ Debian (apt packages) | Alpine = musl (problemi OpenCV) |
| **Python 3.10** | ✅ Match ambiente dev | |
| **GPU Support** | ✅ Installa CUDA dopo | `nvidia/cuda` = 4GB+ |
| **YOLO Fallbacks** | ✅ .onnx/.pt funzionano | |

### Alternative Analizzate

❌ **`python:3.10-alpine`** (~50 MB)
- Problemi: musl libc incompatibile con Python wheels (OpenCV, YOLO)
- Compilazione manuale richiesta

❌ **`python:3.10`** (Debian full, ~1 GB)
- Problemi: 800MB in più per nulla

❌ **`nvidia/cuda:12.0-runtime-ubuntu22.04`** (~4 GB)
- Problemi: Solo GPU, no fallback CPU, troppo specifico

✅ **`python:3.10-slim`** (125 MB)
- **Sweet spot**: Leggero + Compatible + Flessibile

### Supporto GPU Opzionale

**Stessa immagine, due modalità:**

```bash
# Senza GPU (CPU-only)
docker run -p 8000:8000 z21-terminal:pc

# Con GPU (CUDA)
docker run --gpus all -p 8000:8000 z21-terminal:pc
```

**YOLO Model Priority** (automatica):
1. **best_obb.engine** (TensorRT) → Se GPU NVIDIA presente
2. **best_obb.onnx** (ONNX) → CPU-only (fallback)
3. **best_obb.pt** (PyTorch) → CPU-only (fallback finale)

### Network Configuration

```dockerfile
# Container ascolta su tutte le interfacce
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Perché `0.0.0.0`?**
- `localhost` = solo loopback, Tailscale non lo vede
- `0.0.0.0` = tutte le interfacce, Tailscale lo vede

**Port mapping**:
```bash
docker run -p 8000:8000 z21-terminal:pc
# Host:8000 → Container:8000
# Tailscale: 443 → Host:8000 → Container:8000
```

---

## 🚀 Quick Start

### Step 1: Build Docker Image

```bash
# SUL MAC
git add .
git commit -m "feat: aggiungi Docker per PC"
git push origin develop

# SUL PC (via SSH o diretto)
git pull origin develop
cd C:/z21-Terminal

# Build immagine
docker build -f test/docker/Dockerfile.pc -t z21-terminal:pc .
```

**Tempo di build**: ~5-10 minuti

### Step 2: Run Container

```bash
# Con GPU (se disponibile)
docker run --gpus all -d \
  --name z21-terminal \
  -v C:/z21-Terminal/config.local.json:/app/config.local.json:ro \
  -v z21-data:/app/backend/data \
  --restart unless-stopped \
  z21-terminal:pc

# Senza GPU (CPU-only)
docker run -d \
  --name z21-terminal \
  -v C:/z21-Terminal/config.local.json:/app/config.local.json:ro \
  -v z21-data:/app/backend/data \
  --restart unless-stopped \
  z21-terminal:pc
```

### Step 3: Verifica Funzionamento

```bash
# Controlla log
docker logs -f z21-terminal

# Verifica health
curl http://localhost:8000/api/status

# Accesso via Tailscale (HTTPS, senza porta)
# https://gaming-pc.tail9350d7.ts.net/
```

✅ **Fatto!** z21-Terminal è ora in esecuzione in Docker.

---

## 📊 Architettura Container

### Dockerfile Structure

```dockerfile
# 1. Base image leggera
FROM python:3.10-slim

# 2. System dependencies (Node.js, OpenCV)
RUN apt-get update && apt-get install -y ...

# 3. Python dependencies dai requirements.txt esistenti
COPY backend/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY scripts/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/scripts-requirements.txt

# 4. Copia codice esistente
WORKDIR /app
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY web/ ./web/
COPY config.json ./

# 5. Build frontend
RUN cd web && npm ci && npm run build

# 6. Copia YOLO models (.engine, .onnx, .pt)
COPY scripts/models/best_obb.engine ./scripts/models/ || true
COPY scripts/models/best_obb.onnx ./scripts/models/ || true
COPY scripts/models/best_obb.pt ./scripts/models/ || true

# 7. Configurazione
EXPOSE 8000

# 8. Entry point
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Cosa Fa il Dockerfile

**NON ricrea da zero** z21-Terminal. Si limita a:

1. ✅ Installare Node.js (per frontend build)
2. ✅ Installare Python deps dai requirements.txt esistenti
3. ✅ Copiare codice esistente (backend, scripts, web, config)
4. ✅ Build frontend (React + Vite + Tailwind CSS)
5. ✅ Copiare YOLO models (.engine, .onnx, .pt)

**NON fa**:
- ❌ Installare PyTorch CUDA (se presente nel PC, nvidia-docker lo gestisce)
- ❌ Configurare Tailscale (gestito dall'host)
- ❌ Addestrare YOLO model (già pronto)

---

## ⚙️ Configurazione Tailscale

### Funzionalamento

```
Internet (HTTPS)
    ↓ 443
Tailscale Cloud (Funnel)
    ↓ 443
Tailscale Client (Host PC)
    ↓ 443 → localhost:8000
Docker Port Forward
    ↓ 8000:8000
Container (FastAPI)
    ↓ 8000
z21-Terminal
```

### Setup Requirements

1. **Tailscale installato sul PC host**
2. **Tailscale Funnel abilitato** per la porta 8000
3. **Container configurato per ascoltare su 0.0.0.0:8000**

### Verifica Configurazione

```bash
# Verifica Tailscale status
tailscale status

# Verifica Funnel status
tailscale funnel status

# Verifica porta 8000 accessibile
curl http://localhost:8000/api/status

# Verifica HTTPS accessibile
curl https://gaming-pc.tail9350d7.ts.net/api/status
```

### Accesso Publico

```bash
# Funzionamento attuale (senza Docker)
https://gaming-pc.tail9350d7.ts.net/

# Con Docker - STESSO ACCESSO
https://gaming-pc.tail9350d7.ts.net/

# Nessuna differenza per l'utente finale!
```

---

## 🔧 Gestione Container

### Comandi Utili

```bash
# Avvia container
docker start z21-terminal

# Stop container
docker stop z21-terminal

# Riavvia container
docker restart z21-terminal

# Vedi log
docker logs -f z21-terminal

# Entra nel container (debug)
docker exec -it z21-terminal bash

# Rimuovi container
docker rm -f z21-terminal

# Rimuovi immagine
docker rmi z21-terminal:pc
```

### Aggiornamento Container

```bash
# 1. Stop e rimuovi container vecchio
docker stop z21-terminal
docker rm z21-terminal

# 2. Pull nuovo codice
git pull origin develop

# 3. Ricostruisci immagine
docker build -f test/docker/Dockerfile.pc -t z21-terminal:pc .

# 4. Avvia nuovo container
docker run --gpus all -d \
  --name z21-terminal \
  -v C:/z21-Terminal/config.local.json:/app/config.local.json:ro \
  -v z21-data:/app/backend/data \
  --restart unless-stopped \
  z21-terminal:pc
```

### Persistenza Dati

```bash
# Volumes per persistenza dati
-v z21-data:/app/backend/data              # Database SQLite
-v C:/z21-Terminal/config.local.json:...   # Configurazione (read-only)

# I dati persistono anche se rimuovi il container
docker rm z21-terminal  # Dati VOLUMI rimangono
```

---

## 📈 Performance e Ottimizzazioni

### GPU vs CPU

| Configurazione | YOLO FPS | RAM Usage | Setup |
|----------------|----------|-----------|-------|
| **GPU NVIDIA** (TensorRT) | 80-120 | ~1.5 GB | Richiede nvidia-docker |
| **CPU only** (ONNX) | 10-15 | ~2.0 GB | Funziona subito |
| **CPU only** (PyTorch) | 5-10 | ~2.5 GB | Fallback finale |

### Requisiti RAM

Basato su test memoria:

| Componente | Min RAM | Max RAM |
|------------|---------|---------|
| Python runtime | 50 MB | 100 MB |
| FastAPI + WebSocket | 100 MB | 200 MB |
| YOLO (CPU) | 600 MB | 900 MB |
| YOLO (GPU) | 400 MB | 600 MB |
| SQLite database | 10 MB | 50 MB |
| MJPEG video feed | 50 MB | 100 MB |
| **TOTAL (CPU)** | **~1.5 GB** | **~2.5 GB** |
| **TOTAL (GPU)** | **~1.0 GB** | **~1.8 GB** |

**Verdetto PC Windows**: ✅ **Più che adeguato** (probabilmente 16-32 GB RAM)

---

## 🐛 Troubleshooting

### Container non parte

```bash
# Controlla log
docker logs z21-terminal

# Verifica Docker attivo
docker ps
docker ps -a  # Vedi anche container stoppati
```

### Porta 8000 già in uso

```bash
# Verifica cosa usa la porta 8000
netstat -ano | findstr :8000  # Windows
netstat -tulpn | grep 8000    # Linux

# Stop o cambia porta
docker run -p 8001:8000 z21-terminal:pc
```

### Tailscale non raggiunge il container

```bash
# Verifica container ascolta su 0.0.0.0 (non localhost)
docker exec z21-terminal netstat -tulpn | grep 8000

# Verifica port forwarding
docker port z21-terminal

# Verifica Tailscale Funnel
tailscale funnel status
```

### GPU non rilevata nel container

```bash
# Verifica nvidia-docker installato
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi

# Verifica container ha accesso GPU
docker exec z21-terminal nvidia-smi

# Verifica PyTorch vede GPU
docker exec z21-terminal python -c "import torch; print(torch.cuda.is_available())"
```

### YOLO lento (CPU mode)

```bash
# Controlla quale modello sta usando
docker exec z21-terminal ls -lah /app/scripts/models/

# Se .engine manca, verifica GPU disponibile
# Se GPU mancante, YOLO userà .onnx o .pt (più lento)
```

### Frontend non si carica

```bash
# Verifica build frontend completato
docker exec z21-terminal ls -lah /app/web/dist/

# Se vuoto, ricostruisci immagine
docker build -f test/docker/Dockerfile.pc --no-cache -t z21-terminal:pc .
```

### Database non persiste

```bash
# Verifica volumes montati
docker inspect z21-terminal | grep -A 10 Mounts

# Backup database prima di upgrade
docker cp z21-terminal:/app/backend/data/data.db ./data.db.backup
```

---

## 🔒 Sicurezza

### Read-Only Config

```bash
# Monta config.local.json in read-only
-v C:/z21-Terminal/config.local.json:/app/config.local.json:ro
```

### Non esporre porte non necessarie

```bash
# Esponi SOLO la porta 8000
-p 8000:8000

# NON usare -p 80:8000 (evita conflitti)
# NON usare --network host (evita conflitti con host)
```

### Volume persistente isolato

```bash
# Crea volume dedicato per database
docker volume create z21-data
-v z21-data:/app/backend/data
```

### Container Restart Policy

```bash
# Riavvia automatico se crasha
--restart unless-stopped

# Oppure sempre
--restart always
```

---

## 📚 Documentazione Correlata

### Deployment
- **[test/docker/README_PC_DOCKER.md](../test/docker/README_PC_DOCKER.md)** - Dockerfile dettagliato, docker-compose, troubleshooting

### Testing
- **[test/README.md](../test/README.md)** - Test suite completa
- **[test/memory/README_MEMORY.md](../test/memory/README_MEMORY.md)** - Memory testing per requisiti hardware

### Computer Vision
- **[TENSORRT_OPTIMIZATION.md](./TENSORRT_OPTIMIZATION.md)** - TensorRT export workflow
- **[COMPUTER_VISION.md](./COMPUTER_VISION.md)** - YOLO training e tuning

### Altro
- **[JETSON_DEPLOYMENT.md](./JETSON_DEPLOYMENT.md)** - Deployment su NVIDIA Jetson Orin Nano
- **[CHROME_DEVTOOLS_OPTIMIZATION.md](./CHROME_DEVTOOLS_OPTIMIZATION.md)** - Chrome DevTools MCP per testing

---

## 🔄 Migrazione da Installazione Tradizionale

### Prima (Senza Docker)
```
C:/z21-Terminal/
├── backend/           # Codice backend
├── scripts/           # YOLO scripts
├── web/               # Frontend
├── venv/              # Python virtual env
├── node_modules/      # Node dependencies
└── backend/data/      # Database
```

### Dopo (Con Docker)
```
C:/z21-Terminal/       # Solo codice sorgente
Docker volumes:
├── z21-data/          # Database (persiste fuori container)
Docker images:
└── z21-terminal:pc    # Tutto il resto (backend + frontend + deps)
```

### Vantaggi Migrazione

| Aspect | Senza Docker | Con Docker |
|--------|--------------|------------|
| **Setup** | Installa Python, Node, deps | `docker run` |
| **Isolamento** | Conflitti possibili | Zero conflitti |
| **Cleanup** | Manuale | `docker rm` |
| **Portabilità** | Hard-coded su PC | Run ovunque |
| **Aggiornamenti** | Manuale | Rebuild image |
| **Liberà PC** | App occupa risorse | Container background |

### Migration Steps

```bash
# 1. Backup database attuale
cp C:/z21-Terminal/backend/data/data.db ./data.db.backup

# 2. Stop installazione tradizionale
# (Ferma qualsiasi processo z21 running)

# 3. Build Docker image
docker build -f test/docker/Dockerfile.pc -t z21-terminal:pc .

# 4. Avvia container con database backup
docker run --gpus all -d \
  --name z21-terminal \
  -v C:/z21-Terminal/config.local.json:/app/config.local.json:ro \
  -v z21-data:/app/backend/data \
  z21-terminal:pc

# 5. Ripristina database nel volume
docker cp ./data.db.backup z21-terminal:/app/backend/data/data.db

# 6. Verifica funzionamento
docker logs -f z21-terminal
curl http://localhost:8000/api/status
```

---

## ⚠️ Note Importanti

1. **PyTorch CUDA**: Se usi GPU, installa nvidia-docker sul host, NON nel container
2. **Tailscale**: Gestito dall'host, NON nel container
3. **YOLO Models**: .engine/.onnx/.pt copiati da host, fallback automatico
4. **Network**: Container usa `0.0.0.0:8000` per Tailscale Funnel
5. **Persistenza**: Database in volume Docker, non perso se rimuovi container
6. **GPU Opzionale**: Stessa immagine funziona con o senza GPU
7. **Usa `git add .`**: Sempre, non specificare percorsi singoli

---

## 🚀 Next Steps

1. **Crea Dockerfile.pc**: `test/docker/Dockerfile.pc`
2. **Crea docker-compose.pc.yml**: Per deploy semplificato
3. **Testa su PC**: Build e run localmente
4. **Verifica Tailscale**: Accesso HTTPS funziona
5. **Deploy Produzione**: Sostituisci installazione tradizionale
