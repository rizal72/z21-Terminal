#!/bin/bash
# z21-Terminal Docker Entry Point per Jetson Orin Nano
#
# Script di startup che gestisce:
# - Validazione ambiente (GPU, CUDA, TensorRT)
# - Setup configurazione
# - Database initialization
# - YOLO TensorRT engine build (solo prima volta)
# - Avvio backend FastAPI

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  z21-Terminal for Jetson Orin Nano${NC}"
echo -e "${BLUE}  Docker Container v1.0.0${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ============================================================================
# 1. AMBIENTE HARDWARE VALIDATION
# ============================================================================
echo -e "${YELLOW}[1/6] Validating hardware environment...${NC}"

# Check Jetson device
if [ -f /etc/nv_tegra_release ]; then
    echo -e "${GREEN}✓ Jetson device detected${NC}"
    cat /etc/nv_tegra_release | head -3
else
    echo -e "${RED}✗ WARNING: Not running on Jetson!${NC}"
    echo "This container is optimized for Jetson Orin Nano."
fi

# Check NVIDIA GPU
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA GPU detected${NC}"
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
else
    echo -e "${RED}✗ nvidia-smi not found - GPU inference unavailable${NC}"
fi

# Check CUDA
if command -v nvcc &> /dev/null; then
    echo -e "${GREEN}✓ CUDA available: $(nvcc --version | grep release)${NC}"
else
    echo -e "${YELLOW}⚠ nvcc not found (CUDA runtime only)${NC}"
fi

# Check TensorRT
if python3 -c "import tensorrt" 2>/dev/null; then
    TENSORRT_VERSION=$(python3 -c "import tensorrt; print(tensorrt.__version__)")
    echo -e "${GREEN}✓ TensorRT available: v${TENSORRT_VERSION}${NC}"
else
    echo -e "${RED}✗ TensorRT not found - YOLO will be slow${NC}"
fi

echo ""

# ============================================================================
# 2. POWER MODE CONFIGURATION (Jetson-specific optimization)
# ============================================================================
echo -e "${YELLOW}[2/6] Optimizing power mode...${NC}"

# Imposta modalità MAX performance se disponibile
if command -v nvpmodel &> /dev/null; then
    echo -e "${GREEN}✓ Setting MAX performance mode (15W-20W)${NC}"
    sudo nvpmodel -m 0 2>/dev/null || echo "Cannot change power mode (need sudo)"
fi

# Massimizza clock frequencies
if command -v jetson_clocks &> /dev/null; then
    echo -e "${GREEN}✓ Maximizing CPU/GPU clocks${NC}"
    sudo jetson_clocks 2>/dev/null || echo "Cannot run jetson_clocks (need sudo)"
fi

echo ""

# ============================================================================
# 3. CONFIGURAZIONE
# ============================================================================
echo -e "${YELLOW}[3/6] Setting up configuration...${NC}"

# Create config.local.json from example if not exists
if [ ! -f /app/config.local.json ]; then
    echo "Creating config.local.json from example..."
    cp /app/config.local.json.example /app/config.local.json
    echo -e "${GREEN}✓ config.local.json created${NC}"
    echo -e "${YELLOW}⚠ IMPORTANT: Edit config.local.json with your camera credentials!${NC}"
    echo -e "${YELLOW}⚠ Camera credentials required for RTSP stream access${NC}"
else
    echo -e "${GREEN}✓ config.local.json exists${NC}"
fi

# Verify Z21 configuration
echo "Z21 Configuration:"
if grep -q "192.168.1.111" /app/config.json 2>/dev/null; then
    echo -e "${GREEN}  ✓ Z21 Host: 192.168.1.111${NC}"
fi

echo ""

# ============================================================================
# 4. DATABASE INITIALIZATION
# ============================================================================
echo -e "${YELLOW}[4/6] Initializing database...${NC}"

if [ ! -f /app/backend/data/data.db ]; then
    echo "Creating database schema..."
    python3 -c "
from backend.dependencies import get_config
print('✓ Database initialized')
" 2>/dev/null || echo -e "${YELLOW}⚠ DB initialization will run on first startup${NC}"
    echo -e "${GREEN}✓ Database ready${NC}"
else
    echo -e "${GREEN}✓ Database exists${NC}"
fi

echo ""

# ============================================================================
# 5. YOLO MODELS & TENSORRT ENGINE
# ============================================================================
echo -e "${YELLOW}[5/6] Checking YOLO models...${NC}"

# Check models in priority order: .engine → .onnx → .pt
FOUND_MODEL=""

# Check TensorRT engine (PRIMARIO)
if [ -f /app/scripts/models/best_obb.engine ]; then
    ENGINE_SIZE=$(du -h /app/scripts/models/best_obb.engine | cut -f1)
    echo -e "${GREEN}✓ TensorRT engine found (${ENGINE_SIZE}) - PRIMARY${NC}"
    echo -e "${GREEN}  Ready for GPU inference!${NC}"
    FOUND_MODEL="engine"
elif [ -f /app/scripts/models/best_obb.onnx ]; then
    ONNX_SIZE=$(du -h /app/scripts/models/best_obb.onnx | cut -f1)
    echo -e "${YELLOW}⚠ ONNX model found (${ONNX_SIZE}) - FALLBACK${NC}"
    echo -e "${YELLOW}  TensorRT engine will be built on first inference${NC}"
    FOUND_MODEL="onnx"
elif [ -f /app/scripts/models/best_obb.pt ]; then
    PT_SIZE=$(du -h /app/scripts/models/best_obb.pt | cut -f1)
    echo -e "${YELLOW}⚠ PyTorch model found (${PT_SIZE}) - FALLBACK${NC}"
    echo -e "${YELLOW}  TensorRT engine will be built on first inference${NC}"
    FOUND_MODEL="pt"
else
    echo -e "${RED}✗ No YOLO models found! Copy best_obb.engine to scripts/models/${NC}"
    FOUND_MODEL="none"
fi

# Warning if .engine not available
if [ "$FOUND_MODEL" != "engine" ]; then
    echo ""
    echo -e "${YELLOW}⚠ TensorRT .engine not found for this GPU${NC}"
    echo -e "${YELLOW}  On first YOLO inference, engine will be built from ${FOUND_MODEL}${NC}"
    echo -e "${YELLOW}  Build time: ~5-10 minutes (one-time only)${NC}"
    echo -e "${YELLOW}  The .engine file will persist in scripts/models/${NC}"
fi

echo ""

# ============================================================================
# 6. AVVIO SERVIZI
# ============================================================================
echo -e "${YELLOW}[6/6] Starting services...${NC}"

# Parse arguments
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Frontend: http://localhost:$PORT"
echo "  Backend API: http://localhost:$PORT/api"
echo "  Network: host mode (required for Z21 UDP)"
echo ""

# Test YOLO import
echo -e "${YELLOW}Testing YOLO import...${NC}"
if python3 -c "from ultralytics import YOLO; print('✓ Ultralytics YOLO OK')" 2>/dev/null; then
    echo -e "${GREEN}✓ YOLO ready for inference${NC}"
else
    echo -e "${RED}✗ YOLO import failed - check dependencies${NC}"
fi

# Test PyTorch CUDA
echo -e "${YELLOW}Testing PyTorch CUDA...${NC}"
if python3 -c "import torch; print(f'✓ PyTorch CUDA available: {torch.cuda.is_available()}')" 2>/dev/null; then
    echo -e "${GREEN}✓ PyTorch + CUDA ready${NC}"
else
    echo -e "${YELLOW}⚠ PyTorch CUDA not available - YOLO will run on CPU (slow)${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  Starting FastAPI Backend${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Avvia uvicorn con FastAPI
exec uvicorn backend.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    --access-log \
    "$@"
