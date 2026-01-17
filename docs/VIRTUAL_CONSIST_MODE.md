# Phase 4B: Virtual Consist Mode

**Status**: ✅ **COMPLETED** (2025-12-31 → 2025-01-03)

**Goal**: Software-level consist control with automatic CV19 management and real-time speed compensation via Δt feedback.

---

## Overview

Virtual Consist Mode permette di controllare locomotive in consist **SEPARATAMENTE** a livello software, senza modificare manualmente CV19. Il sistema:

1. ✅ **Scrive automaticamente CV19** (operations mode) quando utente toggle mode
2. ✅ **Speed compensation real-time** usando Δt feedback da gate timing (Phase 4)
3. ✅ **UI transparente**: utente vede UN solo slider, app controlla lead/rear separatamente
4. ✅ **Reversibile istantaneamente**: toggle back a DCC mode in 1 click
5. ✅ **Persist state**: `config.json` `consists[id]['virtual_mode']` mantiene mode tra restart

---

## Key Concepts

### DCC Consist Mode (Traditional)
- **CV19 = consist_address** (es. 10, 11)
- Locomotive rispondono SOLO all'address del consist
- Speed/direction inviati al consist address
- Z21 gestisce sincronizzazione hardware

### Virtual Consist Mode (Software)
- **CV19 = 0** (locomotive libere dal consist)
- Locomotive rispondono ai loro address nativi (1, 5, 7, 8)
- App invia comandi separati a lead e rear
- Speed compensation basato su Δt da gate timing

---

## Implementation

### Backend: z21_manager.py

#### enable_virtual_mode()
```python
def enable_virtual_mode(self, consist_address):
    """
    Enable Virtual Mode: write CV19=0 to both locos (operations mode)
    Frees locomotives from DCC consist for individual control.
    """
    consist = self.consists[consist_address]
    lead_addr = consist['lead_address']
    rear_addr = consist['rear_address']

    # Write CV19=0 via operations mode (no programming track needed!)
    success_lead = self.z21.write_cv_ops_mode(lead_addr, 19, 0)
    success_rear = self.z21.write_cv_ops_mode(rear_addr, 19, 0)

    if success_lead and success_rear:
        consist['virtual_mode'] = True
        consist['auto_compensation_enabled'] = True  # Default ON
        self._save_persisted_state()  # Saves to config.json
        return True
    return False
```

#### disable_virtual_mode()
```python
def disable_virtual_mode(self, consist_address):
    """
    Disable Virtual Mode: restore CV19=consist_address
    Returns locomotives to DCC consist mode.
    """
    consist = self.consists[consist_address]
    lead_addr = consist['lead_address']
    rear_addr = consist['rear_address']

    # Restore CV19 to consist address
    success_lead = self.z21.write_cv_ops_mode(lead_addr, 19, consist_address)
    success_rear = self.z21.write_cv_ops_mode(rear_addr, 19, consist_address)

    if success_lead and success_rear:
        consist['virtual_mode'] = False
        consist['auto_compensation_enabled'] = False
        self._save_persisted_state()  # Saves to config.json
        return True
    return False
```

#### set_speed() with Compensation
```python
def set_speed(self, consist_address, speed, direction):
    """
    Set speed with optional Δt compensation in Virtual Mode.
    """
    consist = self.consists[consist_address]
    virtual_mode = consist.get('virtual_mode', False)
    auto_comp = consist.get('auto_compensation_enabled', False)

    if not virtual_mode:
        # DCC mode: send to consist address
        self.z21.set_loco_speed(consist_address, speed, direction)
        return

    # Virtual Mode: control lead and rear separately
    lead_addr = consist['lead_address']
    rear_addr = consist['rear_address']

    speed_lead = speed
    speed_rear = speed

    # Apply Δt compensation if enabled
    if auto_comp and consist.get('delta_t') is not None:
        delta_t = consist['delta_t']

        # Only compensate if |Δt| > threshold (avoid micro-adjustments)
        if abs(delta_t) > 0.1:  # 100ms threshold
            # Δt > 0: lead passes first (too fast) → slow down lead
            # Δt < 0: rear passes first (too fast) → slow down rear
            compensation = int(delta_t * 5)  # 5 speed steps per second Δt

            if delta_t > 0:
                speed_lead = max(0, speed_lead - compensation)
            else:
                speed_rear = max(0, speed_rear + compensation)

    # Send individual commands
    self.z21.set_loco_speed(lead_addr, speed_lead, direction)
    self.z21.set_loco_speed(rear_addr, speed_rear, direction)
```

### State Persistence: config.json

```json
{
  "consists": {
    "10": {
      "name": "Consist 10 - Tracciato Interno",
      "lead_address": 1,
      "rear_address": 5,
      "virtual_mode": false,
      "auto_compensation_enabled": false,
      ...
    },
    "11": {
      "name": "Consist 11 - Tracciato Esterno",
      "lead_address": 7,
      "rear_address": 8,
      "virtual_mode": true,
      "auto_compensation_enabled": true,
      ...
    }
  }
}
```

**File location**: `config.json` (committed to git)

**Persistence**: `z21_manager._save_persisted_state()` saves `virtual_mode` and `auto_compensation_enabled` to config.json after every toggle

---

## Frontend: ConsistController.jsx

### Virtual Mode Toggle UI

```jsx
{/* Virtual Mode Toggle Section */}
{isConsist && (
  <div className="virtual-mode-section">
    <button
      onClick={() => onToggleVirtualMode(selection.address, !item.virtual_mode)}
      className={`toggle-button ${item.virtual_mode ? 'active' : ''}`}
      title={item.virtual_mode ? 'Virtual Mode Active - CV19=0' : 'DCC Consist Mode'}
    >
      <div className="flex items-center gap-2">
        <i className={`fa-solid ${item.virtual_mode ? 'fa-gears' : 'fa-link'}`}
          style={{ color: item.virtual_mode ? '#06d6a0' : '#64748b' }}
        />
        <span>{item.virtual_mode ? 'Virtual Consist Mode' : 'DCC Consist Mode'}</span>
      </div>

      {/* CV19 Status */}
      <div className="cv19-status">
        {item.virtual_mode ? 'CV19=0' : `CV19=${selection.address}`}
      </div>

      {/* Status Indicator */}
      <div className="status-line">
        <span className={item.virtual_mode ? "status-dot green" : "status-dot grey"}>●</span>
        <span>
          {item.virtual_mode
            ? 'Locomotives freed from consist • Individual speed control possible'
            : 'Standard DCC consist • Locomotives synchronized via CV19'
          }
        </span>
      </div>
    </button>

    {/* Auto-Compensation Toggle (only in Virtual Mode) */}
    {item.virtual_mode && (
      <div className="compensation-toggle">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={item.auto_compensation_enabled}
            onChange={() => onToggleAutoCompensation(selection.address)}
          />
          <i className="fa-solid fa-gauge-high"
            style={{ color: item.auto_compensation_enabled ? '#06d6a0' : '#64748b' }}
          />
          <span>Auto Speed Compensation (Δt feedback)</span>
        </label>

        {/* Current Δt Display */}
        {item.delta_t !== undefined && (
          <div className="delta-t-info">
            Current Δt: {item.delta_t > 0 ? '+' : ''}{item.delta_t.toFixed(3)}s
            <span className={`status-${item.delta_t_status}`}>
              {item.delta_t_status === 'SYNCED' ? '🟢' :
               item.delta_t_status === 'WARNING' ? '🟡' : '🔴'}
            </span>
          </div>
        )}
      </div>
    )}
  </div>
)}
```

### WebSocket Handlers

```jsx
// Handle Virtual Mode toggle
const onToggleVirtualMode = (consistAddress, enable) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'toggle_virtual_mode',
      consist_address: consistAddress,
      enable: enable
    }));
  }
};

// Handle Auto-Compensation toggle
const onToggleAutoCompensation = (consistAddress) => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'toggle_auto_compensation',
      consist_address: consistAddress
    }));
  }
};
```

---

## WebSocket Protocol

### toggle_virtual_mode
**Client → Server**:
```json
{
  "type": "toggle_virtual_mode",
  "consist_address": 11,
  "enable": true
}
```

**Server → Client** (broadcast):
```json
{
  "type": "virtual_mode_update",
  "consist_address": 11,
  "virtual_mode": true,
  "auto_compensation_enabled": true,
  "success": true,
  "message": "Virtual Mode enabled for consist 11"
}
```

### toggle_auto_compensation
**Client → Server**:
```json
{
  "type": "toggle_auto_compensation",
  "consist_address": 11
}
```

**Server → Client** (broadcast):
```json
{
  "type": "compensation_update",
  "consist_address": 11,
  "auto_compensation_enabled": false,
  "message": "Auto-compensation disabled for consist 11"
}
```

---

## Speed Compensation Algorithm

### Logic Flow

1. **User moves slider**: target_speed = 80 (example)

2. **Backend receives speed command**:
   - Check if consist in Virtual Mode
   - Check if auto_compensation_enabled
   - Get current Δt from gate timing

3. **Calculate compensation**:
   ```python
   if abs(delta_t) > 0.1:  # Threshold: 100ms
       compensation = int(delta_t * 5)  # 5 steps per second Δt

       if delta_t > 0:  # Lead too fast
           speed_lead = target_speed - compensation
           speed_rear = target_speed
       else:  # Rear too fast
           speed_lead = target_speed
           speed_rear = target_speed + compensation
   ```

4. **Send individual commands**:
   - `z21.set_loco_speed(lead_addr, speed_lead, direction)`
   - `z21.set_loco_speed(rear_addr, speed_rear, direction)`

5. **Δt converges to ~0** over multiple gate crossings

### Example Scenario (Consist 11)

**Initial state**:
- Δt = +0.5s (loco 7 passa 0.5s prima di loco 8)
- User speed = 80

**Compensation applied**:
```
compensation = 0.5 * 5 = 2.5 → 2 steps
speed_lead = 80 - 2 = 78  (slow down loco 7)
speed_rear = 80            (loco 8 unchanged)
```

**After 3-4 gate crossings**:
- Δt = +0.1s (migliorato!)
- Compensation = 0 (sotto threshold)
- Entrambe le loco a speed 80

**Result**: ✅ Sincronizzazione raggiunta

---

## Testing Checklist

### CV19 Operations Mode Write
- [x] ✅ Write CV19=0 to loco 7 (Hornby TXS)
- [x] ✅ Write CV19=0 to loco 8 (ESU LokPilot 5)
- [x] ✅ Verify CV19=0 via JMRI DecoderPro (dopo toggle)
- [x] ✅ Restore CV19=11 (disable Virtual Mode)
- [x] ✅ Verify CV19=11 restored correctly

### Speed Control
- [x] ✅ DCC Mode: slider controlla consist address (10, 11)
- [x] ✅ Virtual Mode: slider controlla lead + rear separatamente
- [x] ✅ Direction change works in both modes
- [x] ✅ Emergency stop works in both modes

### Speed Compensation
- [x] ✅ Auto-compensation toggle visibile solo in Virtual Mode
- [x] ✅ Compensation calculation correct (Δt > 0 → slow lead, Δt < 0 → slow rear)
- [x] ✅ Threshold 100ms prevents micro-adjustments
- [x] ✅ Δt converges to ~0 over multiple crossings

### UI/UX
- [x] ✅ Virtual Mode toggle button con CV19 indicator
- [x] ✅ Status dot: green (Virtual) / grey (DCC)
- [x] ✅ Auto-compensation checkbox disabled in DCC mode
- [x] ✅ Current Δt display con color coding (🟢🟡🔴)
- [x] ✅ WebSocket reconnect preserves Virtual Mode state

### State Persistence
- [x] ✅ config.json updated on every Virtual/DCC Mode toggle
- [x] ✅ State loaded on backend restart (`_load_persisted_state()`)
- [x] ✅ State synced to frontend via initial_state message
- [x] ✅ Multi-consist support (independent Virtual Mode per consist)

---

## Advantages

### vs Traditional DCC Consist
- ✅ **Speed matching automatico** (no manual CV adjustment)
- ✅ **Real-time compensation** (Δt feedback loop)
- ✅ **Reversibile** (toggle back a DCC in 1 click)
- ✅ **No programming track** (tutto operations mode)

### vs JMRI Consist Management
- ✅ **Più veloce** (1 click vs JMRI Consist Tool UI)
- ✅ **Automazione** (speed compensation automatico)
- ✅ **Web UI** (accessibile da tablet/phone)
- ✅ **Live Δt monitoring** (JMRI non ha gate tracking)

---

## Known Limitations

### CV19 Write Compatibility
- ✅ **ESU decoders**: CV write sempre funzionante
- ✅ **Hornby TXS**: CV write funzionante (confermato)
- ⚠️ **Zimo MX630**: Non testato (loco 4 non in uso)

### Speed Compensation Accuracy
- Dipende da **Δt precision** (gate timing detection)
- Richiede **2 gate configurati** per consist
- Compensation factor `5 steps/second` è empirico (può essere tuned)

### Multi-Device Sync
- State sincronizzato via WebSocket broadcast
- Se client disconnesso durante toggle: reconnect fetch state

---

## Future Enhancements

### Phase 5: Advanced Compensation Algorithms
- [ ] PID controller (proporzionale + integrale + derivativo)
- [ ] Adaptive compensation factor (auto-tune)
- [ ] Speed table CV adjustment (permanent tuning)

### Phase 6: Consist Manager UI
- [ ] Create/Edit/Delete consists via web UI
- [ ] Gate assignment per consist
- [ ] Δt history graph (trend over time)

---

## Files Modified

**Backend**:
- `backend/z21_manager.py` - enable/disable_virtual_mode(), speed compensation, _save_persisted_state()
- `backend/main.py` - WebSocket handlers (toggle_virtual_mode, toggle_auto_compensation)

**Frontend**:
- `web/src/components/ConsistController.jsx` - Virtual Mode toggle UI
- `web/src/App.jsx` - WebSocket handlers integration

**Config**:
- `config.json` - Contains `consists[id]['virtual_mode']` and `auto_compensation_enabled` (committed to git)

---

**Date Completed**: 2025-01-03
**Testing**: ✅ Fully tested with Consist 11 (loco 7 + 8)
**Production Status**: ✅ Operational on PC Windows GPU deployment

---

## References

- **Z21 Protocol**: `docs/Z21_PROTOCOL.md` (CV operations mode details)
- **Consist Mapping**: `docs/CONSIST_MAPPING.md` (Lead/Rear vs Reference/Adjust logic)
- **Phase 4 Tracking**: `CLAUDE.md` (Δt gate timing detection implementation)
- **GPU Deployment**: `docs/GPU_DEPLOYMENT.md` (consist_state.json copy instructions)
