# Test Suite - z21-Terminal

Questa cartella contiene gli script di testing per z21-Terminal.

## 📁 Struttura

```
test/
├── memory/                         # Test memoria (Backend + Frontend)
│   ├── backend_memory_monitor.py   # Monitoraggio processo Python
│   ├── frontend_memory_test.js     # Test Chrome DevTools MCP
│   ├── run_full_memory_test.sh     # Script orchestratore completo
│   ├── results/                    # Output dei test (gitignored)
│   └── README_MEMORY.md            # Documentazione specifica test memoria
├── docker/                         # Docker configuration for Jetson
│   ├── Dockerfile.jetson           # Dockerfile per Jetson Orin Nano
│   ├── docker-entrypoint.sh        # Startup script container
│   ├── docker-compose.jetson.yml   # Docker Compose configuration
│   ├── requirements-jetson.txt     # Python dependencies for Jetson
│   └── README_JETSON_DOCKER.md     # Guida completa Docker deployment
└── README.md                       # Questo file
```

## 🚀 Avvio Rapido

### Test Memoria Completo

```bash
# SUL MAC (sviluppo)
# 1. Commit e push i test su GitHub
git add .
git commit -m "test: aggiungi suite memory testing"
git push origin develop

# SUL PC (server) via SSH
# 2. Pull le modifiche
ssh riccardo@gaming-pc "cd C:/z21-Terminal && git pull"

# 3. Esegui test memoria completo (10 minuti)
ssh riccardo@gaming-pc "cd C:/z21-Terminal/test/memory && ./run_full_memory_test.sh"

# 4. Altre opzioni
ssh riccardo@gaming-pc "cd C:/z21-Terminal/test/memory && ./run_full_memory_test.sh --duration 5"
ssh riccardo@gaming-pc "cd C:/z21-Terminal/test/memory && ./run_full_memory_test.sh --backend-only"
```

### Docker Build per Jetson

```bash
# Build immagine Docker per Jetson Orin Nano
docker build -f test/docker/Dockerfile.jetson -t z21-terminal:jetson .

# Oppure usa Docker Compose (consigliato)
docker-compose -f test/docker/docker-compose.jetson.yml build
docker-compose -f test/docker/docker-compose.jetson.yml up -d
```

### Prerequisiti

```bash
# Sul PC server (gaming-pc)
pip install psutil

# Assicurati che l'app sia in esecuzione sul PC
ssh riccardo@gaming-pc "z21-status"
```

## 📊 Risultati

I risultati dei test sono salvati in `test/memory/results/`:

- `backend_memory_TIMESTAMP.csv` - Dati grezzi memoria backend
- `summary_report_TIMESTAMP.md` - Report riassuntivo
- `memory_test.html` - Dashboard frontend per test manuali

## 🐳 Docker per Jetson Orin Nano

### Cos'è L4T (Linux for Tegra)

A differenza di un PC normale, sui Jetson **non puoi usare le immagini Docker standard** di Python perché non contengono i driver per l'hardware NVIDIA.

Le immagini **L4T** includono:
- ✅ CUDA Toolkit
- ✅ cuDNN
- ✅ TensorRT

### Vantaggi Docker L4T

| Caratteristica | Senza Docker | Con Docker L4T |
|----------------|--------------|----------------|
| Installazione CUDA | Manuale, rischioso | Già incluso |
| YOLO Performance | CPU (2-3 FPS) | GPU TensorRT (60-90 FPS) |
| Portabilità | Hard-coded | Run ovunque |

### Quick Deploy

```bash
# 1. Copia file sul Jetson
scp -r test/docker backend web scripts config.json jetson@jetson-orin-nano:/home/jetson/z21-terminal/

# 2. Build e avvia sul Jetson
ssh jetson@jetson-orin-nano
cd /home/jetson/z21-terminal
docker-compose -f test/docker/docker-compose.jetson.yml up -d
```

## 📖 Documentazione

### Testing Memoria
- **[test/memory/README_MEMORY.md](memory/README_MEMORY.md)** - Documentazione completa test memoria
- **[docs/MEMORY_TESTING.md](../docs/MEMORY_TESTING.md)** - Guida principale testing memoria

### Docker Jetson
- **[test/docker/README_JETSON_DOCKER.md](docker/README_JETSON_DOCKER.md)** - Guida completa Docker deployment

### Altro
- **[Chrome DevTools Optimization](../docs/CHROME_DEVTOOLS_OPTIMIZATION.md)** - MCP server setup
- **[TensorRT Optimization](../docs/TENSORRT_OPTIMIZATION.md)** - GPU acceleration
- **[Computer Vision](../docs/COMPUTER_VISION.md)** - YOLO training e deployment

## 🔧 Troubleshooting

### Backend non trovato

```bash
# Verifica che il backend sia in esecuzione
ps aux | grep "python.*main.py"

# Avvia il backend
z21-backend
```

### Frontend non accessibile

```bash
# Verifica che il frontend sia in esecuzione
curl http://localhost:5173

# Avvia il frontend
z21-frontend
```

### psutil non installato

```bash
pip install psutil
```

### Docker build fallisce su Jetson

```bash
# Verifica di essere sull'immagine corretta
docker pull nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.1-py3

# Verifica GPU accessibile
docker run --rm --gpus all nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.1-py3 nvidia-smi
```

## 📝 Note

- I test di memoria sono **non-invasivi** (non modificano il database o la configurazione)
- I risultati sono automaticamente gitignored
- Per test sul Jetson Orin Nano, copia tutta la cartella `test/` sul dispositivo
- I file Docker sono stati generati con l'assistenza di Google Gemini per la scelta della base L4T

## 🔗 Risorse

- [NVIDIA NGC L4T PyTorch](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-pytorch)
- [Jetson Orin Nano Technical Overview](https://developer.nvidia.com/embedded/jetson-orin-nano)
- [Docker on Jetson](https://developer.nvidia.com/embedded/learn/tutorials/v/sensor-docker-camera)
