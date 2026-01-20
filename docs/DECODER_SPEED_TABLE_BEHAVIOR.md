# Decoder Speed Table Behavior

**Project**: z21-Terminal
**Last Updated**: 2026-01-20

---

## Overview

Non tutti i decoder DCC implementano le speed table allo stesso modo. Esistono due approcci principali:

1. **NMRA Standard** - Speed table CVs sovrascrivono completamente Vstart/Vhigh
2. **ESU mfx® Style** - Speed table CVs sono scalati/interpolati tra Vstart/Vhigh

Questa differenza è **critica** per il nostro Speed Table Viewer e per le operazioni di speed matching.

---

## ESU mfx® Style (LokSound, LokPilot)

### Decoders interessati

**Roster z21-Terminal**:
- Loco 1 (Gr.675 017) - ESU LokSound V4.0
- Loco 2 (E656 182) - ESU LokPilot 5
- Loco 5 (D645 014) - ESU LokPilot 5
- Loco 6 (D445 1140) - ESU LokPilot 5
- Loco 8 (E444 056) - ESU LokPilot 5

**Total: 5/7 locomotives** (71% del roster)

### Come funziona

**CV2 (Vstart) e CV5 (Vhigh) sono SEMPRE attivi**:
- CV2 (Vstart) = Velocità minima (speed step 1)
- CV5 (Vhigh) = Velocità massima (speed step 28)
- Tutti i valori intermedi (step 2-27) sono **scalati** per fittare tra Vstart e Vhigh

**CV67-94 (Speed Table)**:
- CV67 (step 1) = **FISSO a 1** (non editabile)
- CV94 (step 28) = **FISSO a 255** (non editabile)
- CV68-93 (step 2-27) = Definiscono la **curva** tra Vstart e Vhigh

**Formula di scaling** (semplificata):
```
Velocità effettiva = Vstart + (CV[step] / 255) * (Vhigh - Vstart)
```

### Esempio pratico

**Configurazione**:
- CV2 (Vstart) = 3
- CV5 (Vhigh) = 91
- CV67 = 1, CV94 = 255 (fissi)
- CV80 (step 14) = 128 (50% della curva)

**Velocità effettive**:
- Speed step 1: 3 + (1/255) * (91-3) ≈ **3.3**
- Speed step 14: 3 + (128/255) * (91-3) ≈ **47.1** (circa metà)
- Speed step 28: 3 + (255/255) * (91-3) = **91**

### Workflow speed matching (ESU)

**JMRI raccomandazione** (dalla screenshot):
> "When speed matching to a loco the Minimum and Maximum speeds MUST be matched first using CVs 2 and 5 ONLY on the LokSound decoder. Then use CVs 68 to 93 to match the remaining 26 speed steps. CVs 2 and 5 MUST be set first when speed matching to another loco."

**Step-by-step**:
1. **Prima fase**: Match CV2 (Vstart) e CV5 (Vhigh) tra le due locomotive
2. **Seconda fase**: Ajusta CV68-93 (step 2-27) per fine-tuning della curva
3. **Non toccare**: CV67/CV94 (sono fissi)

**Perché questo ordine?**
- CV2/CV5 definiscono il **range** (min/max speed)
- CV68-93 definiscono la **forma della curva** dentro quel range
- Se cambi CV2/CV5 dopo aver tuned CV68-93, devi rifare tutto

---

## NMRA Standard

### Decoders interessati

**Roster z21-Terminal**:
- Loco 7 (E656 239) - Hornby TXS
- Loco 4 (2048) - Zimo MX630 (da verificare)

### Come funziona

**Speed Table CVs sovrascrivono Vstart/Vhigh**:
- CV67 (step 1) = Velocità minima (0-255, editabile)
- CV94 (step 28) = Velocità massima (0-255, editabile)
- CV68-93 (step 2-27) = Velocità intermedie (0-255, editabili)
- CV2 (Vstart) e CV5 (Vhigh) = **Ignorati** quando speed table è attiva (CV29 bit 4 = 1)

**Nessuno scaling**:
```
Velocità effettiva = CV[step]  (valore diretto, no interpolazione)
```

### Workflow speed matching (NMRA)

**Step-by-step**:
1. Edita direttamente CV67-94 (step 1-28)
2. Nessuna dipendenza da CV2/CV5
3. Tutti gli step sono indipendenti

---

## Implicazioni per z21-Terminal

### 1. Database schema

**Attuale** (`locomotive_speed_table` table):
```sql
CREATE TABLE locomotive_speed_table (
    address INTEGER PRIMARY KEY,
    step_1 INTEGER, step_2 INTEGER, ..., step_28 INTEGER,  -- CV67-94
    imported_at TIMESTAMP,
    source TEXT
);
```

**Proposto**:
```sql
CREATE TABLE locomotive_speed_table (
    address INTEGER PRIMARY KEY,

    -- Speed table CVs (step 1-28)
    step_1 INTEGER, step_2 INTEGER, ..., step_28 INTEGER,  -- CV67-94

    -- ESU mfx® style - Vstart/Vhigh
    vstart INTEGER,           -- CV2 (NULL for NMRA decoders)
    vhigh INTEGER,            -- CV5 (NULL for NMRA decoders)

    -- Metadata
    decoder_type TEXT,        -- "esu_mfx", "nmra_standard"
    imported_at TIMESTAMP,
    source TEXT
);
```

**Note**:
- `vstart`/`vhigh` = NULL per decoder NMRA (non usati)
- `decoder_type` = Discrimina comportamento UI/editing

### 2. Speed Table Viewer UI

**Attuale**: 28 bar chart, tutti editabili

**Proposto** (ESU decoders):

```
┌─────────────────────────────────────────────────────────────┐
│ Loco 1: Gr.675 017 (ESU LokSound V4.0)                     │
│ Decoder Type: ESU mfx® Style                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────┐                           ┌─────────────┐  │
│ │ CV2 Vstart  │                           │ CV5 Vhigh   │  │
│ │     3       │  [Edit]                   │     91      │  │
│ └─────────────┘                           └─────────────┘  │
│                                                             │
│ Speed Table (CV67-94) - Scaled between Vstart and Vhigh    │
│                                                             │
│ [Step 1]  [Step 2]  [Step 3]  ...  [Step 27]  [Step 28]   │
│   FIXED     EDIT     EDIT    ...     EDIT      FIXED       │
│   (1)       (19)     (29)            (245)     (255)       │
│ ████████  ████████  ████████  ...  ████████  ████████      │
│                                                             │
│ ⚠️  Steps 1 and 28 are FIXED (1 and 255) for ESU decoders │
│ ℹ️  Edit CV2/CV5 to change min/max speed                   │
│ ℹ️  Edit steps 2-27 to shape the curve between endpoints  │
└─────────────────────────────────────────────────────────────┘
```

**Proposto** (NMRA decoders):

```
┌─────────────────────────────────────────────────────────────┐
│ Loco 7: E656 239 (Hornby TXS)                              │
│ Decoder Type: NMRA Standard                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Speed Table (CV67-94) - All steps editable                 │
│                                                             │
│ [Step 1]  [Step 2]  [Step 3]  ...  [Step 27]  [Step 28]   │
│   EDIT     EDIT     EDIT    ...     EDIT      EDIT         │
│   (10)     (19)     (29)            (245)     (255)        │
│ ████████  ████████  ████████  ...  ████████  ████████      │
│                                                             │
│ ℹ️  All steps are editable for NMRA decoders              │
│ ℹ️  CV2 (Vstart) and CV5 (Vhigh) are ignored              │
└─────────────────────────────────────────────────────────────┘
```

**UI elements**:
- **Vstart/Vhigh box** (ESU only): Editable inputs in evidenza sopra la speed table
- **Step 1/28 disabled** (ESU only): Grey out, tooltip "Fixed for ESU decoders"
- **Decoder Type badge**: Visual indicator in header
- **Help text**: Context-specific per decoder type

### 3. Import workflow (`import_single_locomotive.py`)

**Attuale**: Legge solo CV67-94 da roster XML

**Proposto**:
```python
def import_locomotive_speed_table(address):
    # Read CV67-94 (sempre)
    speed_table = read_cvs_67_94_from_roster(address)

    # Detect decoder type
    decoder = get_decoder_type(address)  # From config.json

    if decoder in ["LokSound", "LokPilot"]:
        # ESU mfx® style
        vstart = read_cv2_from_roster(address)
        vhigh = read_cv5_from_roster(address)

        # Force CV67=1, CV94=255 (ignore JMRI values if different)
        speed_table[0] = 1
        speed_table[27] = 255

        db.insert_speed_table(
            address=address,
            steps=speed_table,
            vstart=vstart,
            vhigh=vhigh,
            decoder_type="esu_mfx"
        )
    else:
        # NMRA standard (Hornby TXS, Zimo, etc.)
        db.insert_speed_table(
            address=address,
            steps=speed_table,
            vstart=None,
            vhigh=None,
            decoder_type="nmra_standard"
        )
```

### 4. CV write operations

**Attuale**: Permette scrittura di qualsiasi CV67-94

**Proposto**:
```python
def write_speed_table_step(address, step, value):
    decoder_type = db.get_decoder_type(address)

    if decoder_type == "esu_mfx":
        # ESU: Block writes to step 1 and 28
        if step == 1 or step == 28:
            raise ValueError(
                f"Step {step} is read-only for ESU decoders. "
                "Edit CV2 (Vstart) or CV5 (Vhigh) instead."
            )
        # Write CV68-93 (step 2-27)
        write_cv(address, 66 + step, value)  # CV68-93
    else:
        # NMRA: All steps writable
        write_cv(address, 66 + step, value)  # CV67-94

def write_vstart_vhigh(address, vstart=None, vhigh=None):
    decoder_type = db.get_decoder_type(address)

    if decoder_type != "esu_mfx":
        raise ValueError(
            f"Vstart/Vhigh only editable for ESU decoders. "
            f"Loco {address} uses {decoder_type}."
        )

    if vstart is not None:
        write_cv(address, 2, vstart)  # CV2
    if vhigh is not None:
        write_cv(address, 5, vhigh)   # CV5
```

### 5. Decoder type detection

**Source**: `config.json` → `locomotives.X.decoder`

**Mapping**:
```python
DECODER_TYPES = {
    "LokSound V4.0": "esu_mfx",
    "LokPilot 5": "esu_mfx",
    "Hornby TXS": "nmra_standard",
    "Zimo MX630": "nmra_standard",  # TBD: Verify
}

def get_decoder_type(address):
    config = load_config()
    decoder_name = config["locomotives"][str(address)]["decoder"]
    return DECODER_TYPES.get(decoder_name, "nmra_standard")  # Default NMRA
```

---

## Speed Matching Strategy

### Scenario: Match Loco 1 (ESU) + Loco 5 (ESU) in Consist 10

**Phase 1: Match endpoints (CV2/CV5)**:
1. Run both locos at speed step 1 (slowest)
2. Adjust CV2 (Vstart) on slower loco until they match
3. Run both locos at speed step 28 (fastest)
4. Adjust CV5 (Vhigh) on faster loco until they match

**Phase 2: Fine-tune curve (CV68-93)**:
1. Run both locos at speed step 14 (mid-point)
2. Adjust CV80 on adjust loco to match
3. Repeat for other critical steps (7, 21, etc.)

**Phase 3: YOLO tracking validation**:
1. Enable Virtual Consist Mode
2. Run automatic speed compensation
3. Monitor Δt trends in Analytics

### Scenario: Match Loco 7 (Hornby TXS) + Loco 8 (ESU) in Consist 11

**⚠️ Mixed decoder types - complex!**

**Option A: Use NMRA-style on ESU**:
- Disable CV2/CV5 on Loco 8 (set to extreme values, rely on CV67-94)
- Match CV67-94 directly on both locos
- ❌ **Problem**: ESU still scales, non-linear behavior

**Option B: Match endpoints + Virtual Mode**:
- Match CV2/CV5 on Loco 8 to Loco 7's CV67/CV94
- Use Virtual Consist Mode for real-time compensation
- ✅ **Recommended**: Simpler, YOLO tracking handles fine-tuning

**Current setup** (Consist 11):
- Virtual Mode: **Enabled**
- Auto Compensation: **Enabled**
- Strategy: Let YOLO tracking compensate for decoder differences

---

## Zimo MX630 Decoder (Loco 4)

**Status**: ⚠️ **To be verified**

Zimo decoders support multiple speed table modes. Need to check:
- Current CV29 bit 4 (speed table enabled?)
- Does it use Vstart/Vhigh scaling like ESU?
- Or pure NMRA style?

**Action**: Test with JMRI DecoderPro and document behavior.

---

## References

- **JMRI DecoderPro**: ESU LokSound 5 decoder definition
- **ESU Documentation**: LokProgrammer manual (mfx® speed table section)
- **NMRA Standards**: S-9.2.2 (Speed Table Configuration Variables)

---

## Next Steps

1. ✅ Document decoder differences (this file)
2. ⏳ Propose database schema changes
3. ⏳ Design Speed Table Viewer UI (ESU vs NMRA modes)
4. ⏳ Implement CV2/CV5 editing for ESU decoders
5. ⏳ Update import script to read CV2/CV5
6. ⏳ Add decoder type detection (config.json)
7. ⏳ Test with Zimo MX630 (Loco 4)
8. ⏳ Update CONSIST_ROSTER.md with decoder notes

---

**End of DECODER_SPEED_TABLE_BEHAVIOR.md**
