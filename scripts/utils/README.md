# YOLO Training Workflow

Workflow completo per creare e trainare modelli YOLO per tracking locomotive.

## 🎯 Workflow Steps

### Step 1: Record Video
```bash
cd scripts/utils
python3 1_record_video.py
```
- Camera credentials loaded from `camera_config.json` (see example file)
- Premi **R** per iniziare/fermare registrazione
- Fai fare 5-10 giri completi al consist sul tracciato
- Video salvato in: `data/videos/camera_video_YYYYMMDD_HHMMSS.mp4`

### Step 2: Extract Frames
```bash
python3 2_extract_frames.py data/videos/camera_video_XXXXXX.mp4 --interval 10
```
- Estrae 1 frame ogni 10 (da ~150s video = ~224 immagini)
- Frame salvati in: `data/frames/img_0001.jpg`, `img_0002.jpg`, etc.

### Step 3: Annotate on Roboflow
1. Upload frames da `data/frames/` su https://roboflow.com
2. Annota con bounding boxes:
   - Classe 1: `E656_lead` (locomotiva davanti)
   - Classe 2: `E444_rear` (locomotiva dietro)
3. Train/Test Split: **80% / 20%**
4. Augmentation: Flip, Crop, Rotation, Brightness
5. Export → Generate → Download in formato **YOLOv8**

### Step 4: Train on Google Colab
1. Apri https://colab.research.google.com
2. Runtime → Change runtime type → **GPU T4**
3. Copia codice da `3_train_yolo_colab.py`
4. **CRITICAL**: Set `RECTANGULAR` flag based on Roboflow preprocessing:
   - `RECTANGULAR = False` → Square 640x640 (CPU-optimized, faster inference)
     - Roboflow preprocessing: "Stretch to 640x640"
   - `RECTANGULAR = True` → Rectangular 640x1152 (GPU-optimized, better accuracy)
     - Roboflow preprocessing: "Fit within 1280x1280"
5. Script auto-fetches latest Roboflow version (no manual version update needed)
6. Run training (~4 minutes for 50 epochs)
7. Download `best.pt` from file panel

### Step 5: Deploy Model
```bash
# Sposta modello trainato (rinomina con version number)
mv ~/Downloads/best.pt ~/Documents/_PROGETTI/z21-Terminal/scripts/models/BiancAlice_v6.pt

# Crea symlink per modello attivo
cd ~/Documents/_PROGETTI/z21-Terminal/scripts/models
ln -sf BiancAlice_v6.pt best.pt

# Update inference size in config.json
# - Square model (640x640): "yolo_imgsz": 640
# - Rectangular model (640x1152): "yolo_imgsz": [640, 1152]
```

### Step 6: Test Tracking
```bash
cd ~/Documents/_PROGETTI/z21-Terminal/scripts
python3 track_consist_yolo.py
```
- Camera credentials loaded from `camera_config.json`
- Usa `models/best.pt` di default
- Oppure specifica modello: `--model models/consist11_v2.pt`

## 📁 Directory Structure

```
utils/
├── 1_record_video.py       # Step 1: Registra video tracciato
├── 2_extract_frames.py     # Step 2: Estrai frame da video
├── 3_train_yolo_colab.py   # Step 4: Training su Colab
│
├── data/
│   ├── videos/             # Video registrati dalla camera (.mp4)
│   ├── frames/             # Frame estratti NUOVI (per prossimi training)
│   └── frames_v1_uploaded/ # Frame v1 già caricati su Roboflow (backup)
│
└── cv_operations/          # CV tools (read/write CV via Z21)
    ├── read_cv_from_roster.py
    ├── test_cv_read.py
    └── test_cv_write.py
```

## ⚠️ Git Ignore

**File NON committati su git** (`.gitignore`):
- `models/*.pt` - Modelli trainati (binari grandi)
- `data/videos/*.mp4` - Video registrati
- `data/frames/*.jpg` - Frame estratti
- `*.zip` - Dataset Roboflow

**File committati su git**:
- Script Python (`.py`)
- Documentazione (`.md`)
- Configurazioni

## 🔄 Iterative Improvements

Per migliorare il modello:
1. Registra più video (diverse condizioni luce, posizioni)
2. Annota più frame su Roboflow (target: 150-200 originali)
3. Set `RECTANGULAR` flag based on deployment target (CPU vs GPU)
4. Re-train su Google Colab (script auto-fetches latest Roboflow version)
5. Salva nuova versione: `BiancAlice_v6.pt`, `BiancAlice_v7.pt`, etc.
6. Test new model: compare mAP50 and real-world detection confidence
7. Aggiorna symlink `best.pt` se il nuovo modello è migliore

## 📊 Model Versioning

**Naming convention**: `BiancAlice_v{N}.pt` (layout name + version)

**Model History**:
- `BiancAlice_v3.pt` - Initial training (137 images, mAP50 = 80.7%)
- `BiancAlice_v4.pt` - Rectangular 640x1152 for GPU (mAP50 = 0.919)
- `BiancAlice_v5.pt` - **ACTIVE** Square 640x640 for CPU (mAP50 = **0.931** ✅)
- `best.pt` - Symlink to active model (currently → BiancAlice_v5.pt)

**Training Modes**:
- **Square (v5)**: 640x640, CPU-optimized, fastest inference, best mAP
- **Rectangular (v4)**: 640x1152, GPU-optimized, reserved for future PC deployment

**Deployment Strategy**:
- **Mac (current)**: v5 square - symlinked as `best.pt`
- **PC GPU (future)**: v4 rectangular - will replace symlink when GPU available
- **Switching**: `ln -sf BiancAlice_vX.pt best.pt` + update `config.json` → `tracking.yolo_imgsz`

**Tips**:
- Keep old versions as backup (v3, v4 saved in `scripts/models/`)
- Always test new model before updating `best.pt` symlink
- Document versions with date and metrics (mAP50, training mode, deployment target)
- Use `config.json` → `tracking.yolo_imgsz` to match model inference size
