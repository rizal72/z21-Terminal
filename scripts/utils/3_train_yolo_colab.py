"""
YOLOv8 Training Script for Google Colab
z21-Terminal - Multi-Locomotive Tracking

Trains YOLO model to recognize locomotives on layout.
Uses DCC address as class prefix for direct mapping.

⚠️ IMPORTANT: Class Names Convention
- Use DCC address (CV1) as prefix: "1_Gr675_017", "7_E656_239", etc.
- NEVER change locomotive DCC addresses after training!
- Changing CV1 breaks class mapping and requires full re-training.

Instructions:
1. Open Google Colab: https://colab.research.google.com
2. New Notebook
3. Runtime → Change runtime type → GPU (T4)
4. Copy-paste this entire script in a code cell
5. Run (Ctrl+Enter)
6. Download trained model: best.pt
"""

# ============================================
# CONFIGURATION - Change version number here
# ============================================
MODEL_VERSION = 3  # ⚠️ UPDATE THIS: Roboflow dataset version (1, 2, 3, etc.)
PROJECT_NAME = "BiancAlice"  # Model identifier (layout name)

# ============================================
# STEP 1: Install Dependencies
# ============================================
print("📦 Installing ultralytics (YOLOv8)...")
!pip install ultralytics roboflow -q

# ============================================
# STEP 2: Download Dataset from Roboflow
# ============================================
print("\n📥 Downloading dataset from Roboflow...")

from roboflow import Roboflow

rf = Roboflow(api_key="8nIuiAbHCUu79WNHaXsI")
# Project name (lowercase URL-friendly)
project = rf.workspace("rizal72").project("biancalice")
version = project.version(MODEL_VERSION)
dataset = version.download("yolov8")

print(f"✅ Dataset downloaded to: {dataset.location}")

# ============================================
# STEP 3: Train YOLOv8 Model
# ============================================
print("\n🚂 Starting YOLOv8 training...")

from ultralytics import YOLO

# Load YOLOv8 nano (fastest, smallest)
model = YOLO('yolov8n.pt')

# Train
results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=50,              # Number of training epochs
    imgsz=512,              # Image size (match Roboflow preprocessing)
    batch=16,               # Batch size (adjust if GPU memory issues)
    name=f'{PROJECT_NAME}_v{MODEL_VERSION}',
    patience=10,            # Early stopping after 10 epochs no improvement
    device=0,               # GPU device (0 = first GPU)
    project='runs/detect',  # Output directory
    verbose=True
)

print("\n✅ Training complete!")

# ============================================
# STEP 4: Validate Model
# ============================================
print("\n📊 Validating model...")

metrics = model.val()

print(f"\n📈 Results:")
print(f"   mAP50: {metrics.box.map50:.3f}")
print(f"   mAP50-95: {metrics.box.map:.3f}")

# ============================================
# STEP 5: Test Inference on Sample Image
# ============================================
print("\n🔍 Testing inference on sample image...")

# Get first train image
import os
train_images = os.listdir(f"{dataset.location}/train/images")
sample_image = f"{dataset.location}/train/images/{train_images[0]}"

# Run inference
results = model(sample_image, conf=0.5)

# Display results
from IPython.display import Image, display
results[0].save("test_prediction.jpg")
display(Image("test_prediction.jpg"))

print(f"\n✅ Inference test complete!")

# ============================================
# STEP 6: Download Trained Model
# ============================================
print("\n💾 Model saved at:")
print(f"   runs/detect/{PROJECT_NAME}_v{MODEL_VERSION}/weights/best.pt")
print(f"\n📥 Download 'best.pt' from the Files panel (left sidebar)")

model_name = f"{PROJECT_NAME}_v{MODEL_VERSION}.pt"

print("\n🎉 Training pipeline complete!")
print(f"\n📝 Next steps (Model: {model_name}):")
print("   1. Download 'best.pt' to your Mac")
print("   2. Rename with version number:")
print(f"      mv ~/Downloads/best.pt ~/Downloads/{model_name}")
print("   3. Place in models folder:")
print(f"      mv ~/Downloads/{model_name} ~/Documents/_PROGETTI/z21-Terminal/scripts/models/")
print("   4. Create/update symlink for active model:")
print("      cd ~/Documents/_PROGETTI/z21-Terminal/scripts/models")
print(f"      ln -sf {model_name} best.pt")
print("   5. Test tracking:")
print("      cd ~/Documents/_PROGETTI/z21-Terminal/scripts")
print("      python3 track_consist_yolo.py")
print(f"\n💡 Note: To train v{MODEL_VERSION + 1}, update MODEL_VERSION = {MODEL_VERSION + 1} at the top of this script")
print(f"\n⚠️  REMEMBER: Never change DCC addresses (CV1) after training!")
