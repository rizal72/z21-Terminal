# CV3/CV4 Acceleration/Deceleration Editor

**Status**: ✅ Implemented (2026-01-20)
**Location**: Settings > Locomotives tab
**Related**: Speed Table Viewer, TEST/NORMAL Mode Toggle

---

## Overview

UI editor for CV3 (Acceleration) and CV4 (Deceleration) in `config.json` without JMRI.

**Why**: During speed table tuning we work with momentum off (CV3=CV4=0). When we activate accel/decel, the speed table tuning may be affected. Need to quickly test different CV3/CV4 values.

---

## Current Situation (Before Implementation)

- CV3/CV4 values hardcoded in `config.json` → `locomotives.X.cv_profiles.normal` and `testing`
- Toggle TEST/NORMAL (hotkey `T`) writes values from config to decoder
- Modifying values requires: JMRI + manual config.json edit

---

## UI Design

**Location**: Settings > Locomotives tab, inside each locomotive accordion

**Order**: CV3/CV4 section → Separator → Functions list

**Layout** (Compact, 2-row design):
```
┌─ CV3/CV4 Box (bordered, bg-slate-900/50) ──────────┐
│ Accel/Decel (Normal Mode): CV3 [78] CV4 [58]      │
│ ℹ️ Values applied when pressing T (toggle mode).   │
│    Test mode always uses CV3=CV4=0.                │
└─────────────────────────────────────────────────────┘

─────────────── (separator border-t) ─────────────────

┌─ Functions Box ────────────────────────────────────┐
│ Functions                                           │
│ F0: Light    [Lockable ☐]                         │
│ F1: Sound    [Lockable ☑]                         │
│ ...                                                 │
└─────────────────────────────────────────────────────┘
```

**Visual Separation**: Two distinct bordered boxes (similar to Vstart/Vhigh ESU panel in SpeedTableViewer)

---

## Workflow

1. **User edits CV3/CV4** in Settings → **Saves only in config.json** (does NOT write to decoder immediately)
2. **User presses hotkey `T`** → Toggle TEST/NORMAL → **At that point** writes CV3/CV4 to decoder
3. **Edited values are active only in NORMAL mode** (test mode always CV3=CV4=0)

---

## Implementation Details

### Frontend (SettingsModal.jsx)

**Components**:
- Two `<input type="number">` fields (CV3, CV4)
  - Range: 0-255
  - Width: `w-16` (compact)
  - Validation: `Math.min(255, Math.max(0, parseInt(value) || 0))`
- Info note with `<kbd>T</kbd>` tag for hotkey reference
- Flex layout: `flex-wrap` for mobile responsiveness

**State Management**:
```jsx
setSettings({
  ...settings,
  locomotives: {
    ...settings.locomotives,
    [address]: {
      ...loco,
      cv_profiles: {
        ...loco.cv_profiles,
        normal: {
          ...loco.cv_profiles?.normal,
          cv3: value  // or cv4
        }
      }
    }
  }
});
```

### Backend

**Already implemented** - no changes needed:
- `/api/settings/update` saves config.json (existing endpoint)
- Toggle TEST/NORMAL reads `cv_profiles.normal` and writes CV3/CV4 to decoder via POM (existing logic)

---

## Config Structure

**config.json**:
```json
{
  "locomotives": {
    "1": {
      "name": "Gr.675 017",
      "decoder": "LokSound V4.0",
      "cv_profiles": {
        "normal": {
          "cv3": 78,   // ← Editable via UI
          "cv4": 58    // ← Editable via UI
        },
        "testing": {
          "cv3": 0,    // ← Always 0 (not editable)
          "cv4": 0     // ← Always 0 (not editable)
        }
      }
    }
  }
}
```

---

## Testing Checklist

1. **Open Settings** → Locomotives tab
2. **Expand accordion** (e.g., Address 1: Gr.675 017)
3. **Verify UI**:
   - CV3/CV4 box appears BEFORE Functions list
   - Bordered box with two inline number inputs
   - Info note with kbd `T` reference
   - Visual separator (border-t) between CV3/CV4 and Functions
4. **Test editing**:
   - Change CV3 value (e.g., 78 → 80)
   - Change CV4 value (e.g., 58 → 60)
   - Verify input validation (0-255 range enforced)
5. **Save settings** → Verify config.json updated
6. **Press hotkey `T`** → Verify decoder receives new CV3/CV4 values

---

## Future Enhancements

### Possible Improvements (Not Planned)

1. **CV3/CV4 Write Button**: Direct write to decoder (bypass hotkey T)
   - Similar to speed table "Write All" button
   - Use case: Test CV3/CV4 changes without toggling mode

2. **CV Profiles Manager**: Multiple profiles (e.g., "Fast", "Slow", "Realistic")
   - Dropdown to switch between profiles
   - Quick-load presets for common scenarios

3. **Decay Rate CV Editor**: CV23/CV24 (momentum decay rate)
   - Advanced tuning for ESU decoders
   - See ESU decoder manual for details

---

## Related Documents

- **[SPEED_TABLE_VIEWER.md](SPEED_TABLE_VIEWER.md)** - Speed table CV67-94 editor
- **[JMRI_INTEGRATION.md](JMRI_INTEGRATION.md)** - JMRI independence roadmap
- **[SETTINGS_UI_DESIGN.md](SETTINGS_UI_DESIGN.md)** - Settings modal structure
- **[FUTURE_IDEAS.md](FUTURE_IDEAS.md)** - Original feature spec (Quick Win section)

---

**Last Updated**: 2026-01-20
