# YOLO Training Workflow

Workflow completo per creare e trainare modelli YOLO per tracking locomotive.

## 🎯 Workflow Steps

### Step 1: Record Video
```bash
cd scripts/utils
python3 1_record_video.py <username> <password>
```
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
4. Aggiorna `version = project.version(2)` se necessario
5. Run training (~30-60 min)
6. Download `best.pt` dal file panel

### Step 5: Deploy Model
```bash
# Sposta modello trainato
mv ~/Downloads/best.pt ~/Documents/_PROGETTI/z21-Terminal/scripts/models/consist11_v1.pt

# Crea symlink per modello attivo
cd ~/Documents/_PROGETTI/z21-Terminal/scripts/models
ln -sf consist11_v1.pt best.pt
```

### Step 6: Test Tracking
```bash
cd ~/Documents/_PROGETTI/z21-Terminal/scripts
python3 track_consist_yolo.py <username> <password>
```
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
2. Annota più frame (target: 100-200 originali)
3. Re-train su Google Colab
4. Salva nuova versione: `consist11_v2.pt`, `consist11_v3.pt`, etc.
5. Aggiorna symlink `best.pt` se il nuovo modello è migliore

## 📊 Model Versioning

**Naming convention**:
- `consist11_v1.pt` - Primo training (46 img originali, 138 augmented)
- `consist11_v2.pt` - Secondo training (più dati, condizioni diverse)
- `consist10_v1.pt` - Futuro: altro consist
- `best.pt` - Symlink al modello attivo corrente

**Tips**:
- Mantieni vecchie versioni come backup
- Testa sempre nuovo modello prima di sostituire `best.pt`
- Annota versioni con date e metriche (mAP50, mAP50-95)
