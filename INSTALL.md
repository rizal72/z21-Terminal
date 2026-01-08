# Installation Guide

## Requirements Files Structure

The project uses separate requirements files for different environments:

| File | Target | Description |
|------|--------|-------------|
| `backend/requirements.txt` | All | FastAPI backend dependencies |
| `scripts/requirements.txt` | All | YOLO tracking + OpenCV (no PyTorch) |
| `requirements-cpu.txt` | macOS | PyTorch CPU-only (lighter) |
| `requirements-gpu.txt` | Windows PC | PyTorch GPU with CUDA 11.8 |

---

## macOS Development Setup (CPU-only)

```bash
cd ~/Documents/_PROGETTI/z21-Terminal

# Option A: System Python (Homebrew)
pip3 install -r backend/requirements.txt
pip3 install -r scripts/requirements.txt
pip3 install -r requirements-cpu.txt

# Option B: Virtual Environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r scripts/requirements.txt
pip install -r requirements-cpu.txt
```

---

## Windows PC Production Setup (GPU + CUDA)

**Prerequisites:**
1. Python 3.11 installed
2. NVIDIA GPU with CUDA support
3. CUDA Toolkit 11.8 installed ([download](https://developer.nvidia.com/cuda-11-8-0-download-archive))

```powershell
# Clone repository
git clone git@github.com:rizal72/z21-Terminal.git
cd z21-Terminal

# Create virtual environment (REQUIRED on Windows)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r backend\requirements.txt
pip install -r scripts\requirements.txt
pip install -r requirements-gpu.txt
```

**Verify GPU setup:**
```python
import torch
print(torch.cuda.is_available())      # Must be True
print(torch.cuda.get_device_name(0))  # Shows GPU name
```

---

## Conda Environment (Alternative)

If you prefer Conda over venv:

```bash
# Create environment
conda create -n z21 python=3.11
conda activate z21

# Install dependencies
pip install -r backend/requirements.txt
pip install -r scripts/requirements.txt

# macOS: CPU version
pip install -r requirements-cpu.txt

# Windows PC: GPU version (CUDA 11.8 required)
pip install -r requirements-gpu.txt
```

---

## Troubleshooting

### PyTorch GPU not working on Windows
- Verify CUDA installed: `nvcc --version`
- Check GPU visibility: `nvidia-smi`
- Reinstall PyTorch: `pip uninstall torch torchvision && pip install -r requirements-gpu.txt`

### Import errors on macOS
- Check Python version: `python3 --version` (must be 3.11+)
- Update pip: `pip3 install --upgrade pip`
- Reinstall dependencies: `pip3 install --force-reinstall -r requirements-cpu.txt`

---

## Next Steps

After installation, see:
- **README.md** - Project overview and usage
- **docs/GPU_DEPLOYMENT.md** - Windows PC deployment guide
- **docs/WEB_DASHBOARD.md** - Frontend development workflow
