# 🗺️ Track Occupancy Map - Implementation Status

**Feature**: Real-time locomotive position visualization on SVG track map
**Status**: ⏸️ **POSTPONED** - Piano completo disponibile, implementazione rimandata
**Data planning**: 2025-01-07
**Motivo postpone**: Video feed esistente già sufficiente, complessità vs beneficio non giustificata al momento

**⚠️ TODO DOMANI**: Creare feature branch `feature/track-occupancy-map` da `develop`
```bash
git checkout develop
git checkout -b feature/track-occupancy-map
```

**📍 Location**: `docs/TRACK_MAP_IMPLEMENTATION.md` (workspace notes, NON committare)

---

## 🎯 Obiettivo

Visualizzazione real-time delle posizioni delle locomotive (L1, L5, L7, L8) su mappa SVG del plastico BiancAlice, con:
- Locomotive markers (cerchi colorati con info)
- Direction indicators (arrows)
- Tunnel interpolation (C10 galleria ~5s blind spot)
- Track paths (Tracciato Esterno ovale + Tracciato Interno figura-8)
- Gate overlays (G1-G4)

---

## ⚠️ CRITICAL: Perspective Correction

**Camera**: Prospettiva obliqua da destra plastico (1280x720)
**SVG**: Top-down orthogonal plane (600x1200)

**Transform necessaria**:
- Source points: 4 angoli plastico in camera coords
- Dest points: rettangolo 600x1200
- Matrix: `cv2.getPerspectiveTransform()` da commit `810404b`
- Scale: 6 px/cm sul corrected plane

**Implementazione**: Backend transform (in `backend/main.py`)
- Frontend riceve coordinate già trasformate
- Single source of truth, più efficiente

---

## 📋 Componenti da Creare (5 files)

1. **TrackMapView.jsx** - Main container
   - Path: `web/src/components/TrackMapView.jsx`
   - Container con header + TrackMapSVG

2. **TrackMapSVG.jsx** - SVG rendering
   - Path: `web/src/components/TrackMapSVG.jsx`
   - ViewBox: `"0 0 600 1200"`
   - Layers: background, tracks, tunnel, gates, markers

3. **LocomotiveMarker.jsx** - Individual marker
   - Path: `web/src/components/LocomotiveMarker.jsx`
   - Circle + arrow + info label (foreignObject)

4. **useLocomotivePositions.js** - Position state hook
   - Path: `web/src/hooks/useLocomotivePositions.js`
   - Tunnel entry/exit detection
   - Linear interpolation (5s blind spot)
   - Re-association logic

5. **perspectiveTransform.js** - Transform utility (optional)
   - Path: `web/src/utils/perspectiveTransform.js`
   - Frontend fallback se backend non fa transform

---

## 🔧 Modifiche File Esistenti (4 files)

1. **App.jsx**
   - Add: `currentView` state ('controllers' | 'trackmap')
   - Add: `yoloDetections` state
   - Add: View toggle buttons (navbar desktop)
   - Add: Conditional rendering (main)
   - Handle: `yolo_detections` WebSocket message

2. **MobileMenu.jsx**
   - Add props: `onViewChange`, `currentView`
   - Add: VIEW section prima di ACTIONS
   - Controllers/Track Map buttons con check icon

3. **backend/main.py**
   - Add: `transform_camera_to_plane()` function
   - Add: `broadcast_yolo_detections()` enriched
   - Modify: yolo_detections handler (call broadcast)
   - Import: cv2, numpy

4. **config.json**
   - Add: "tunnel" section (zone, duration, consist)

---

## 📅 Implementation Phases

### Phase 1: Foundation (2-3h) ← **START HERE**
- [x] Create TrackMapSVG.jsx skeleton (viewBox 600x1200)
- [x] Create TrackMapView.jsx container
- [x] Add currentView state to App.jsx
- [x] Add view toggle buttons (navbar)
- [x] Add conditional rendering (main)
- [x] Modify MobileMenu.jsx (VIEW section)
- [x] Test: view switching works

### Phase 2: Locomotive Markers (2-3h)
- [ ] Create LocomotiveMarker.jsx
- [ ] Add yoloDetections state to App.jsx
- [ ] Backend: enrich detections (speed/direction)
- [ ] Backend: perspective transform
- [ ] Render markers in TrackMapSVG
- [ ] Test: markers follow locomotive positions

### Phase 3: Tunnel Interpolation (3-4h)
- [ ] Create useLocomotivePositions.js hook
- [ ] Implement tunnel entry/exit detection
- [ ] Implement linear interpolation (5s)
- [ ] Visual indication (dimmed, dashed)
- [ ] Re-association logic
- [ ] Add tunnel zone to config.json
- [ ] Test: C10 through tunnel interpolates correctly

### Phase 4: Track Paths (1-2h)
- [ ] Ridisegna tracks da PNG (SVG path editor)
- [ ] Replace placeholder paths in TrackMapSVG
- [ ] Add depot zones (red rects)
- [ ] Test: visual accuracy vs real layout

### Phase 5: Polish & Testing (2-3h)
- [ ] Responsive design (mobile/desktop)
- [ ] Performance optimization (React.memo, useMemo)
- [ ] Error handling (WebSocket offline, missing data)
- [ ] Animation smoothness (CSS transitions)
- [ ] Multi-device testing
- [ ] Documentation

**Total Estimate**: 12-18 hours

---

## 🔑 Quick Reference

**Plan file**: `~/.claude/plans/sparkling-mapping-kite.md`
**Layout PNG**: `docs/track_layout_with_gates.png`
**Legacy perspective code**: `git show 810404b:scripts/track_consist_yolo.py`
**Gates config**: `config.json` (camera coords [1280x720])

**Gate positions** (camera coords):
- G1: [1227, 213] - C11 orange
- G2: [133, 149] - C11 orange
- G3: [1086, 326] - C10 cyan
- G4: [479, 29] - C10 cyan

**Locomotive markers**:
- C10 (Tracciato Interno): cyan #00ffff
- C11 (Tracciato Esterno): orange #ffa500

---

## 📦 Backend Perspective Transform Code

```python
# backend/main.py (da aggiungere)
import cv2
import numpy as np

# Source points (4 angoli plastico in camera frame)
SRC_POINTS = np.float32([
    [7, 246],      # Top-left (far corner)
    [376, 31],     # Top-right (far corner)
    [957, 37],     # Bottom-right (near corner)
    [257, 718]     # Bottom-left (near corner)
])

# Destination points (rettangolo corrected plane)
DST_WIDTH = 600
DST_HEIGHT = 1200
Y_OFFSET = 50
LAYOUT_HEIGHT = 950

DST_POINTS = np.float32([
    [0, Y_OFFSET],
    [DST_WIDTH, Y_OFFSET],
    [DST_WIDTH, Y_OFFSET + LAYOUT_HEIGHT],
    [0, Y_OFFSET + LAYOUT_HEIGHT]
])

# Extended points (vedi tracks oltre P3-P4)
p1, p2, p3, p4 = SRC_POINTS
p3_ext = [p3[0] + (p3[0] - p2[0]) * 0.05, p3[1] + (720 - p3[1]) * 0.3]
p4_ext = [p4[0] - (p1[0] - p4[0]) * 0.05, p4[1] + (720 - p4[1]) * 0.3]

PERSPECTIVE_MATRIX = cv2.getPerspectiveTransform(
    np.float32([p1, p2, p3_ext, p4_ext]),
    DST_POINTS
)

def transform_camera_to_plane(point):
    """Transform camera coordinates to corrected plane."""
    pt = np.float32([[point]])  # Shape (1,1,2)
    transformed = cv2.perspectiveTransform(pt, PERSPECTIVE_MATRIX)
    return transformed[0][0].tolist()  # [x, y]

async def broadcast_yolo_detections(detections):
    """Broadcast enriched + transformed YOLO detections."""
    enriched_detections = []

    for det in detections.get('detections', []):
        address = det.get('address')
        camera_pos = det.get('position')

        # Transform coordinates
        plane_pos = transform_camera_to_plane(camera_pos)

        # Lookup speed/direction
        loco_state = None
        for consist_addr, consist in consist_data.items():
            if consist.get('lead_address') == address or consist.get('rear_address') == address:
                loco_state = consist
                break

        enriched_detections.append({
            **det,
            'position': plane_pos,  # TRANSFORMED!
            'camera_position': camera_pos,  # Original for debug
            'speed': loco_state.get('speed', 0) if loco_state else 0,
            'direction': loco_state.get('direction', 'forward') if loco_state else 'forward',
            'in_consist': consist_addr if loco_state else None
        })

    message = {
        'type': 'yolo_detections',
        'detections': enriched_detections,
        'timestamp': detections.get('timestamp')
    }

    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            pass
```

---

## ✅ Checklist Prima di Committare

**Phase 1 completata quando**:
- [ ] View toggle funziona (desktop buttons)
- [ ] Mobile menu mostra VIEW section
- [ ] SVG placeholder visibile in Track Map view
- [ ] No console errors
- [ ] Responsive (mobile/tablet/desktop)

**Files da committare**:
- `web/src/components/TrackMapView.jsx` (NEW)
- `web/src/components/TrackMapSVG.jsx` (NEW)
- `web/src/App.jsx` (MODIFIED)
- `web/src/components/MobileMenu.jsx` (MODIFIED)

**Files NON committare**:
- CLAUDE.md (privato)
- .claude/ (privato)
- docs/TRACK_MAP_IMPLEMENTATION.md (questo file - workspace notes)

---

**Prossimo step**: Phase 1 Task 1 - Create TrackMapSVG.jsx 🚀
