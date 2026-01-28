# Jetson Orin Nano Docker Deployment - z21-Terminal

**Version**: 1.0.0
**Last Updated**: 2026-01-28
**Purpose**: Dockerizzare l'ambiente z21-Terminal esistente per Jetson Orin Nano

---

## 🎯 Overview

Questa guida spiega come **dockerizzare z21-Terminal** per deployment su Jetson Orin Nano. Il progetto è già completo e funzionante su Mac/PC - qui ci concentriamo SOLO su:

1. **Ottimizzazione CUDA/Jetson** (non setup da zero)
2. **TensorRT integration** per YOLO
3. **Best practices Docker** per ambienti embedded

## 📋 Prerequisiti

### Hardware
- **Jetson Orin Nano** (8GB consigliato, 4GB possibile)
- Scheda microSD 32GB+ (Class 10)
- Alimentatore NVIDIA originale

### Software su Jetson
- **JetPack SDK** 5.1+ (inclusa Ubuntu 20.04 LTS)
- **Docker Engine** (già incluso in JetPack)
- **Docker Compose** (opzionale ma consigliato)

```bash
# Verifica installazione Docker
docker --version
docker-compose --version
```

## 🚀 Quick Start

### 1. Deploy Codice sul Jetson

```bash
# SUL MAC (sviluppo)
# 1. Commit e push tutto su GitHub
git add .
git commit -m "feat: aggiorna per deployment Jetson"
git push origin develop

# SUL JETSON via SSH
# 2. Clone o pull del repository
ssh jetson@jetson-orin-nano
cd /home/jetson/z21-terminal
git pull origin develop

# Se è la prima volta:
# git clone git@github.com:rizal72/z21-Terminal.git
# cd z21-terminal
```

### 2. Configurazione

```bash
# Sul Jetson (gia connessi via SSH)
cd /home/jetson/z21-terminal

# Crea config.local.json con credenziali camera
cp config.local.json.example config.local.json
nano config.local.json  # Inserisci username/password camera RTSP
```

### 3. Build Docker Image

```bash
# Opzione A: Dockerfile diretto
docker build -f test/docker/Dockerfile.jetson -t z21-terminal:jetson .

# Opzione B: Docker Compose (consigliato)
docker-compose -f test/docker/docker-compose.jetson.yml build
```

**Nota**: Il richiede circa 10-15 minuti per:
- Installare Node.js e dipendenze Python
- Buildare il frontend React
- Preparare l'ambiente YOLO

### 4. Avvio Container

```bash
# Opzione A: Docker run
docker run --gpus all -p 8000:8000 --network host \
  -v $(pwd)/config.local.json:/app/config.local.json \
  -v z21-data:/app/backend/data \
  --name z21-terminal \
  z21-terminal:jetson

# Opzione B: Docker Compose (consigliato)
docker-compose -f test/docker/docker-compose.jetson.yml up -d
```

### 5. Verifica Funzionamento

```bash
# Controlla log
docker-compose -f test/docker/docker-compose.jetson.yml logs -f

# Verifica health
curl http://localhost:8000/api/status

# Apri dashboard
# Dal Jetson: http://localhost:8000
# Da altro device: http://<JETSON_IP>:8000
```

## 🐳 Cosa Fa il Dockerfile

Il Dockerfile **NON ricrea da zero** z21-Terminal. Si limita a:

1. **Parte da L4T-PyTorch** (PyTorch + CUDA + TensorRT già inclusi)
2. **Install Node.js** per il frontend build
3. **Install Python deps** dai requirements.txt esistenti:
   - `backend/requirements.txt` (FastAPI, uvicorn, websockets)
   - `scripts/requirements.txt` (ultralytics, opencv)
4. **Copy codice esistente** (backend, scripts, web, config)
5. **Build frontend** (React + Vite + Tailwind CSS)
6. **Copy YOLO models** (.pt e .onnx esistenti)

**NON fa** (perché non serve):
- ❌ Installare PyTorch (già nell'immagine L4T)
- ❌ Configurare CUDA (già configurato)
- ❌ Addestrare YOLO model (già pronto best_obb.pt)
- ❌ Creare da zero il progetto (già esistente)

## 📊 Ottimizzazioni Jetson

### 1. Power Mode (NVP Model)

Il container imposta automaticamente la modalità MAX performance:

```bash
# Nel docker-entrypoint.sh
sudo nvpmodel -m 0  # MAX performance mode (15W-20W)
sudo jetson_clocks  # Massimizza CPU/GPU/EMC clocks
```

### 2. TensorRT Engine

Il file TensorRT (`.engine`) è **specifico per ogni GPU**.

**Priorità modelli in z21-Terminal**:
1. **best_obb.engine** (TensorRT) - PRIMARIO, compilato per GPU specifica
2. **best_obb.onnx** (ONNX) - Fallback se .engine non disponibile
3. **best_obb.pt** (PyTorch) - Fallback finale per export

**Workflow automatico**:
1. Al primo avvio, yolo_tracker.py cerca `best_obb.engine` per la GPU corrente
2. Se non presente (o per GPU diversa), lo compila automaticamente dal primo disponibile (.onnx → .pt)
3. Tempo di compilazione: **5-10 minuti** (solo al primo avvio)
4. Il file `.engine` viene salvato in `scripts/models/` e persiste

**Nota**: Non precompiliamo `.engine` nel Docker build perché:
- Il build potrebbe girare su Mac (x86_64) e il Jetson è ARM64
- L'engine è specifico per ogni GPU (Orin Nano ha GPU diversa da Orin NX, etc.)
- yolo_tracker.py ha già la logica di compilazione automatica

### 3. Swap File

Il Jetson ha RAM limitata. Raccomandato aggiungere swap:

```bash
# Crea 4GB swap file
sudo fallocate -l 4G /mnt/4GB.swap
sudo chmod 600 /mnt/4GB.swap
sudo mkswap /mnt/4GB.swap
sudo swapon /mnt/4GB.swap

# Rendi permanente
echo '/mnt/4GB.swap none swap sw 0 0' | sudo tee -a /etc/fstab
```

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

# Aumenta swap (vedi sezione 3 sopra)
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

## 📝 Aggiornamento Container

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

## 📈 Performance Attese

| Configurazione | YOLO FPS | RAM Usage | VRAM Usage | Note |
|----------------|----------|-----------|------------|------|
| Jetson Orin Nano 8GB (MAX performance) | 60-90 | ~1.5 GB | ~1 GB | ✅ Raccomandato |
| Jetson Orin Nano 4GB (MAX performance) | 50-70 | ~2.5 GB | ~1 GB | ⚠️ Margini ridotti |
| Jetson Orin Nano 8GB (15W mode) | 40-60 | ~1.2 GB | ~800 MB | ✅ Buon compromise |

## 🔒 Sicurezza

### Non montare config.local.json in scrittura

```yaml
# In docker-compose.jetson.yml
volumes:
  - ./config.local.json:/app/config.local.json:ro  # Read-only!
```

### Usa rete host per Z21 UDP

```yaml
# Z21 protocol usa UDP broadcast
network_mode: host  # Necessario per Z21 communication
```

### Limita risorse se necessario (4GB model)

```yaml
deploy:
  resources:
    limits:
      memory: 3.5G
```

## 📚 Documentazione Correlata

- **[Docker Performance](../docs/DOCKER_PERFORMANCE.md)** - Ottimizzazioni Docker avanzate
- **[TensorRT Optimization](../docs/TENSORRT_OPTIMIZATION.md)** - TensorRT export workflow
- **[Computer Vision](../docs/COMPUTER_VISION.md)** - YOLO training e tuning
- **[Test Suite](../test/README.md)** - Testing memoria e performance

## 🔗 Risorse Esterne

- [NVIDIA NGC L4T PyTorch](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch)
- [Jetson Orin Nano Technical Overview](https://developer.nvidia.com/embedded/jetson-orin-nano)
- [TensorRT Documentation](https://docs.nvidia.com/deeplearning/tensorrt/)
- [Docker on Jetson](https://developer.nvidia.com/embedded/learn/tutorials/v/sensor-docker-camera)

## ⚠️ Note Importanti

1. **PyTorch è già incluso** nell'immagine L4T - NON reinstallarlo
2. **Il TensorRT .engine** è specifico per ogni GPU - viene generato sul Jetson
3. **Usa requirements.txt esistenti** - non ricrearli da zero
4. **Network mode host** è necessario per Z21 UDP broadcast
5. **Power mode MAX** è raccomandato per performance YOLO ottimali
