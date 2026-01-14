# Phase 6: Consist Manager UI + Mobile Header

**Status**: ✅ **COMPLETED** (2025-01-03)

**Goal**: Complete web UI for consist management with mobile-optimized header

**Implementation Summary**:
- ✅ Phase 6A: Mobile Header with hamburger menu (<768px) - `MobileMenu.jsx`
- ✅ Phase 6B: Consist Manager CRUD operations - `ConsistManagerModal.jsx`, `ConsistCard.jsx`, `ConsistForm.jsx`
- ✅ Backend API: `/api/consists` (GET/POST/PUT/DELETE), `/api/restart-daemon`
- ✅ Integration: Desktop inline button + Mobile menu item
- ✅ Production: Deployed and tested on Mac (dev) and PC (production)

---

## Phase Overview

### Phase 6A: Mobile Header Refactor (prerequisite)
Implement responsive header with hamburger menu for mobile to prevent overflow when adding [⚙️ Consists] button.

### Phase 6B: Consist Manager UI
Modal interface for CRUD operations on consists, integrated with gate_config.json.

---

## Phase 6A: Mobile Header Refactor

### Problem Statement

**Current header on mobile** (<768px):
```
┌──────────────────────────────────────────────┐
│ 🚂 [🔄] [🌙]  <space>  [+]  [STOP]  ⚡📶🖥️   │
└──────────────────────────────────────────────┘

9 elements: Logo, Reload, Wake Lock, Spacer, Add, STOP, 3×Status
```

**Problem**: No room for [⚙️ Consists] button without overflow or wrapping.

### Solution: Hamburger Menu (Mobile Only)

**Desktop/Tablet** (≥768px): No changes, inline layout:
```
┌────────────────────────────────────────────────────────────┐
│ 🚂 z21 Terminal  [🔄 Reload] [🌙]  [+]  [⚙️ Consists]      │
│   DCC Controller                   [STOP ALL]  ⚡📶🖥️       │
└────────────────────────────────────────────────────────────┘
```

**Mobile** (<768px): Hamburger menu:
```
┌──────────────────────────────────────────────┐
│ 🚂  [≡]  <────spacer────>  [STOP]  ⚡📶🖥️    │
└──────────────────────────────────────────────┘

Left: Logo + Hamburger
Center: Spacer (flex-grow)
Center-right: Emergency STOP (always visible, safety critical)
Right: 3 status indicators (always visible, monitoring)
```

**Slide-in Menu** (click [≡] on mobile):
```
┌────────────────────────┐
│ [× Close]              │
├────────────────────────┤
│ ⚙️ Consist Manager     │ ← NEW in Phase 6B
│ ➕ Add Controller       │
│ 🔄 Reload Roster       │
│ 🌙 Keep Screen Awake   │
└────────────────────────┘

Overlay: Semi-transparent backdrop
Animation: Slide from right (300ms ease-out)
Width: 280px
Position: Fixed right, full height
```

### Design Rationale

**What stays always visible on mobile**:
- ✅ **Logo** (brand identity)
- ✅ **Emergency STOP** (safety critical - center position)
- ✅ **Status icons** (⚡ Track Power, 📶 WebSocket, 🖥️ Z21 - monitoring essential)
- ✅ **Hamburger [≡]** (access to secondary actions)

**What moves to menu**:
- ⚙️ Consist Manager (new)
- ➕ Add Controller (less frequent action)
- 🔄 Reload Roster (maintenance action)
- 🌙 Keep Screen Awake (toggle action)

**Benefits**:
- Clean mobile header (5 elements vs 9+)
- STOP always accessible at center (muscle memory)
- Status always visible (real-time monitoring)
- Room for future features in menu

### Implementation Details

#### 1. New State (`App.jsx`)

```jsx
const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
```

#### 2. Header Component Structure

```jsx
<header className="...">
  <div className="flex items-center gap-4">
    {/* Left: Logo + Hamburger (mobile) or Full Title (desktop) */}
    <div className="flex items-center gap-3">
      <i className="fa-solid fa-train ..."></i>

      {/* Mobile: Hamburger */}
      <button
        onClick={() => setMobileMenuOpen(true)}
        className="md:hidden px-2 py-2 ..."
      >
        <i className="fa-solid fa-bars text-xl"></i>
      </button>

      {/* Desktop/Tablet: Full title */}
      <div className="hidden md:block">
        <h1>z21 Terminal</h1>
        <p>DCC Locomotive Controller</p>
      </div>
    </div>

    {/* Desktop only: Inline actions */}
    <div className="hidden md:flex items-center gap-3">
      <button onClick={handleReloadRoster}>...</button>
      {/* Keep Screen Awake - desktop only if desired */}
      <button onClick={addController}>+</button>
      <button onClick={() => setConsistManagerOpen(true)}>
        ⚙️ Consists
      </button>
    </div>

    {/* Spacer */}
    <div className="flex-grow"></div>

    {/* Emergency STOP - always visible */}
    <button className="emergency-stop">...</button>

    {/* Status Icons - always visible */}
    <div className="flex items-center gap-2">
      <div>⚡</div>
      <div>📶</div>
      <div>🖥️</div>
    </div>
  </div>
</header>

{/* Mobile Menu Overlay */}
{mobileMenuOpen && (
  <MobileMenu
    onClose={() => setMobileMenuOpen(false)}
    onConsistManager={() => {
      setMobileMenuOpen(false);
      setConsistManagerOpen(true);
    }}
    onAddController={() => {
      setMobileMenuOpen(false);
      addController();
    }}
    onReloadRoster={() => {
      setMobileMenuOpen(false);
      handleReloadRoster();
    }}
    onWakeLock={() => {
      // Toggle wake lock
    }}
  />
)}
```

#### 3. MobileMenu Component

```jsx
// components/MobileMenu.jsx
export default function MobileMenu({
  onClose,
  onConsistManager,
  onAddController,
  onReloadRoster,
  onWakeLock,
  wakeLockActive,
  reloadingRoster
}) {
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-[60] md:hidden"
        onClick={onClose}
      />

      {/* Menu Panel */}
      <div className="fixed right-0 top-0 h-full w-[280px] bg-control-dark border-l border-control-grey z-[70] md:hidden animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-control-grey">
          <h2 className="text-lg font-display font-semibold text-signal-amber">
            Menu
          </h2>
          <button
            onClick={onClose}
            className="text-track-steel hover:text-signal-amber transition-colors"
          >
            <i className="fa-solid fa-times text-xl"></i>
          </button>
        </div>

        {/* Menu Items */}
        <div className="p-4 space-y-3">
          {/* Consist Manager */}
          <button
            onClick={onConsistManager}
            className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left"
          >
            <i className="fa-solid fa-gears text-signal-amber text-xl"></i>
            <span className="font-sans text-sm">Consist Manager</span>
          </button>

          {/* Add Controller */}
          <button
            onClick={onAddController}
            className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left"
          >
            <i className="fa-solid fa-plus text-signal-green text-xl"></i>
            <span className="font-sans text-sm">Add Controller</span>
          </button>

          {/* Reload Roster */}
          <button
            onClick={onReloadRoster}
            disabled={reloadingRoster}
            className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left disabled:opacity-50"
          >
            <i className={`fa-solid ${reloadingRoster ? 'fa-spinner fa-spin' : 'fa-rotate-right'} text-track-steel text-xl`}></i>
            <span className="font-sans text-sm">
              {reloadingRoster ? 'Reloading...' : 'Reload Roster'}
            </span>
          </button>

          {/* Keep Screen Awake */}
          {'wakeLock' in navigator && (
            <button
              onClick={onWakeLock}
              className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left"
            >
              <i className={`fa-solid fa-moon text-xl ${wakeLockActive ? 'text-signal-green' : 'text-track-steel'}`}></i>
              <span className="font-sans text-sm">
                {wakeLockActive ? 'Screen Awake ✓' : 'Keep Screen Awake'}
              </span>
            </button>
          )}
        </div>
      </div>
    </>
  );
}
```

#### 4. Animation CSS

```css
/* index.css */
@keyframes slide-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.animate-slide-in {
  animation: slide-in 300ms ease-out;
}
```

### Testing Checklist

- [ ] Mobile (<768px): Hamburger visible, inline actions hidden
- [ ] Desktop (≥768px): Hamburger hidden, inline actions visible
- [ ] Menu slide-in animation smooth (300ms)
- [ ] Backdrop closes menu on click
- [ ] [×] Close button works
- [ ] STOP button always centered on mobile
- [ ] Status icons always visible on mobile
- [ ] Menu items trigger correct actions and close menu

---

## Phase 6B: Consist Manager UI

### Goal

Web UI for managing consists stored in `gate_config.json` without editing JSON manually or requiring JMRI.

**NOTE**: Virtual Mode toggle is **already implemented** in `ConsistController.jsx` (Phase 4B ✅). This phase focuses on CRUD operations only.

### Features

1. **List Consists**: Show all consists from gate_config.json
2. **Create Consist**: Add new consist (lead + rear addresses, name, gate assignment)
3. **Edit Consist**: Modify existing consist
4. **Delete Consist**: Remove consist from config
5. **Gate Assignment**: Checkbox/dropdown to assign gates to consist
6. **Single Loco Support**: Create "consist of 1" (rear_address = null)
7. **Persist Changes**: Save to gate_config.json and notify daemon to reload

### UI Design

#### Desktop/Tablet: Inline Button

```
Header right side:
[🔄 Reload] [+] [⚙️ Consists] [STOP] ⚡📶🖥️
```

#### Mobile: From Hamburger Menu

```
Menu:
⚙️ Consist Manager  ← Click opens modal
```

#### Consist Manager Modal

```
┌──────────────────────────────────────────────────┐
│ ⚙️ Consist Manager                         [×]   │
├──────────────────────────────────────────────────┤
│                                                  │
│  Consist 11 - Tracciato Esterno (Ovale)         │
│  ┌────────────────────────────────────────────┐ │
│  │ Lead: Loco 7 (E656 239)                    │ │
│  │ Rear: Loco 8 (E444 056)                    │ │
│  │ Gates: [✓] Gate 1  [✓] Gate 2             │ │
│  │                                            │ │
│  │ Current Δt: +0.234s 🟢 SYNCED             │ │
│  │ 23 gate crossings this session             │ │
│  │                                            │ │
│  │ [Edit] [Delete]                            │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  Consist 10 - Tracciato Interno (Figura 8)      │
│  ┌────────────────────────────────────────────┐ │
│  │ Lead: Loco 1 (Gr.675 017)                  │ │
│  │ Rear: Loco 5 (D645 014)                    │ │
│  │ Gates: [  ] Gate 1  [  ] Gate 2            │ │
│  │        [  ] Gate 3  [  ] Gate 4            │ │
│  │                                            │ │
│  │ ⚠️ No gates assigned - tracking disabled   │ │
│  │                                            │ │
│  │ [Edit] [Delete]                            │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  Loco 8 - E444 056 (Single)                     │
│  ┌────────────────────────────────────────────┐ │
│  │ Address: 8                                 │ │
│  │ Type: Single Locomotive                    │ │
│  │ Gates: [✓] Gate 1  [✓] Gate 2             │ │
│  │                                            │ │
│  │ ℹ️ Position tracking only (no Δt)          │ │
│  │                                            │ │
│  │ [Edit] [Delete]                            │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  [+ Create New Consist]                          │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Create/Edit Form

```
┌──────────────────────────────────────────────────┐
│ Create New Consist                         [×]   │
├──────────────────────────────────────────────────┤
│                                                  │
│  Name:                                           │
│  [________________________________]              │
│                                                  │
│  Type:                                           │
│  ( ) Traditional Consist (2 locomotives)         │
│  ( ) Single Locomotive                           │
│                                                  │
│  Lead Locomotive:                                │
│  Address: [___]  Name: [__________________]      │
│                                                  │
│  Rear Locomotive: (disabled if single)           │
│  Address: [___]  Name: [__________________]      │
│                                                  │
│  Gate Assignment:                                │
│  Select gates this consist will cross:          │
│  [  ] Gate 1 - Bottom Right (vicino)             │
│  [  ] Gate 2 - Top Left (lontano)                │
│  [  ] Gate 3 - (not configured)                  │
│  [  ] Gate 4 - (not configured)                  │
│                                                  │
│  ⚠️ Note: Δt tracking requires 2 locomotives     │
│           AND exactly 2 gates assigned.          │
│                                                  │
│  [Cancel] [Save]                                 │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Backend API

#### Endpoints

**GET `/api/consists`**
```json
{
  "consists": {
    "11": {
      "name": "Consist 11 - Tracciato Esterno (Ovale)",
      "lead_address": 7,
      "rear_address": 8,
      "gate_ids": [1, 2]
    },
    "10": { ... },
    "8": {
      "name": "Loco 8 - E444 056 (Single)",
      "lead_address": 8,
      "rear_address": null,
      "gate_ids": [1, 2]
    }
  },
  "gates": [
    {"id": 1, "name": "Bottom Right (vicino)", ...},
    {"id": 2, "name": "Top Left (lontano)", ...}
  ]
}
```

**POST `/api/consists`** (Create)
```json
Request:
{
  "consist_id": 12,
  "name": "Consist 12 - New Consist",
  "lead_address": 3,
  "rear_address": 4,
  "gate_ids": [1, 2]
}

Response:
{
  "status": "success",
  "message": "Consist 12 created",
  "restart_required": true
}
```

**PUT `/api/consists/:id`** (Update)
```json
Request:
{
  "name": "Updated Name",
  "gate_ids": [3, 4]
}

Response:
{
  "status": "success",
  "message": "Consist 11 updated",
  "restart_required": true
}
```

**DELETE `/api/consists/:id`** (Delete)
```json
Response:
{
  "status": "success",
  "message": "Consist 10 deleted",
  "restart_required": true
}
```

**POST `/api/restart-daemon`** (Reload config)
```json
Response:
{
  "status": "success",
  "message": "Tracking daemon restarted with new config"
}
```

#### Backend Implementation

```python
# backend/main.py

@app.get("/api/consists")
async def get_consists():
    """Get all consists and available gates from gate_config.json"""
    config = load_gate_config()
    return {
        "consists": config.get("tracking_assignments", {}),
        "gates": config.get("gates", [])
    }

@app.post("/api/consists")
async def create_consist(consist_data: dict):
    """Create new consist in gate_config.json"""
    config = load_gate_config()

    consist_id = str(consist_data["consist_id"])
    config["tracking_assignments"][consist_id] = {
        "name": consist_data["name"],
        "lead_address": consist_data["lead_address"],
        "rear_address": consist_data.get("rear_address"),  # Can be null
        "gate_ids": consist_data.get("gate_ids", []),
        "notes": f"Created via UI on {datetime.now().isoformat()}"
    }

    save_gate_config(config)

    return {
        "status": "success",
        "message": f"Consist {consist_id} created",
        "restart_required": True
    }

@app.put("/api/consists/{consist_id}")
async def update_consist(consist_id: str, updates: dict):
    """Update existing consist"""
    config = load_gate_config()

    if consist_id not in config["tracking_assignments"]:
        raise HTTPException(status_code=404, detail="Consist not found")

    # Update fields
    for key, value in updates.items():
        if key in ["name", "lead_address", "rear_address", "gate_ids"]:
            config["tracking_assignments"][consist_id][key] = value

    save_gate_config(config)

    return {
        "status": "success",
        "message": f"Consist {consist_id} updated",
        "restart_required": True
    }

@app.delete("/api/consists/{consist_id}")
async def delete_consist(consist_id: str):
    """Delete consist"""
    config = load_gate_config()

    if consist_id not in config["tracking_assignments"]:
        raise HTTPException(status_code=404, detail="Consist not found")

    del config["tracking_assignments"][consist_id]
    save_gate_config(config)

    return {
        "status": "success",
        "message": f"Consist {consist_id} deleted",
        "restart_required": True
    }

@app.post("/api/restart-daemon")
async def restart_daemon():
    """Restart tracking daemon to reload gate_config.json"""
    global tracking_manager

    # Stop current daemon
    await tracking_manager.stop()

    # Start new daemon (will reload config)
    await tracking_manager.start()

    return {
        "status": "success",
        "message": "Tracking daemon restarted"
    }

def save_gate_config(config: dict):
    """Save gate_config.json"""
    with open(GATE_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
```

### Frontend Components

#### ConsistManagerModal.jsx

```jsx
import { useState, useEffect } from 'react';

export default function ConsistManagerModal({ isOpen, onClose, apiUrl }) {
  const [consists, setConsists] = useState({});
  const [gates, setGates] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingConsist, setEditingConsist] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadConsists();
    }
  }, [isOpen]);

  const loadConsists = async () => {
    const response = await fetch(`${apiUrl}/api/consists`);
    const data = await response.json();
    setConsists(data.consists);
    setGates(data.gates);
  };

  const handleDelete = async (consistId) => {
    if (!confirm(`Delete consist ${consistId}?`)) return;

    await fetch(`${apiUrl}/api/consists/${consistId}`, {
      method: 'DELETE'
    });

    await loadConsists();
    alert('Consist deleted. Restart daemon to apply changes.');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-control-dark border-2 border-control-grey rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-control-grey">
          <h2 className="text-xl font-display font-semibold text-signal-amber">
            ⚙️ Consist Manager
          </h2>
          <button
            onClick={onClose}
            className="text-track-steel hover:text-signal-amber transition-colors"
          >
            <i className="fa-solid fa-times text-xl"></i>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-120px)]">
          {showCreateForm || editingConsist ? (
            <ConsistForm
              consist={editingConsist}
              gates={gates}
              onSave={async (data) => {
                // Create or update
                await loadConsists();
                setShowCreateForm(false);
                setEditingConsist(null);
              }}
              onCancel={() => {
                setShowCreateForm(false);
                setEditingConsist(null);
              }}
            />
          ) : (
            <>
              {/* List Consists */}
              <div className="space-y-4">
                {Object.entries(consists).map(([id, consist]) => (
                  <ConsistCard
                    key={id}
                    consistId={id}
                    consist={consist}
                    gates={gates}
                    onEdit={() => setEditingConsist({ id, ...consist })}
                    onDelete={() => handleDelete(id)}
                  />
                ))}
              </div>

              {/* Create Button */}
              <button
                onClick={() => setShowCreateForm(true)}
                className="mt-4 w-full p-3 bg-control-black border border-signal-green text-signal-green rounded hover:bg-signal-green/10 transition-colors"
              >
                <i className="fa-solid fa-plus mr-2"></i>
                Create New Consist
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

### Implementation Checklist

**Phase 6A: Mobile Header**
- [ ] Add hamburger button (mobile only)
- [ ] Create MobileMenu component with slide-in animation
- [ ] Move Reload/Wake Lock/Add Controller to menu on mobile
- [ ] Keep STOP + Status icons always visible
- [ ] Test responsive breakpoints (768px)
- [ ] Test menu animations and backdrop

**Phase 6B: Consist Manager**
- [ ] Create ConsistManagerModal component
- [ ] Create ConsistCard component (list item)
- [ ] Create ConsistForm component (create/edit)
- [ ] Backend: GET /api/consists
- [ ] Backend: POST /api/consists (create)
- [ ] Backend: PUT /api/consists/:id (update)
- [ ] Backend: DELETE /api/consists/:id
- [ ] Backend: POST /api/restart-daemon
- [ ] Frontend: Gate assignment checkboxes
- [ ] Frontend: Single loco support (rear = null)
- [ ] Frontend: Real-time Δt display (if tracking active)
- [ ] Integration: [⚙️ Consists] button in desktop header
- [ ] Integration: Menu item in mobile hamburger
- [ ] Testing: CRUD operations persist to gate_config.json
- [ ] Testing: Daemon reload after config changes

### Success Criteria

- ✅ Mobile header clean (5 elements max)
- ✅ STOP always centered on mobile
- ✅ Status icons always visible
- ✅ Hamburger menu smooth slide-in (300ms)
- ✅ Desktop header inline with [⚙️ Consists] button
- ✅ Create/Edit/Delete consists via UI
- ✅ Gate assignment UI works
- ✅ Single loco support (rear_address = null)
- ✅ Changes persist to gate_config.json
- ✅ Daemon auto-restarts or prompts user
- ✅ No JMRI required for consist management

---

**Priority**: HIGH (eliminates JMRI dependency completely)

**Estimated Effort**: 1-2 days (6A: 4-6 hours, 6B: 6-8 hours)

**Dependencies**: Phase 4B (Virtual Mode already complete ✅), Phase 5 (Config-driven tracking ✅)
