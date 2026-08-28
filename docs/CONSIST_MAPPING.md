# Consist Mapping: Lead/Rear vs Reference/Adjust

**Last Updated**: 2026-01-02

---

## Executive Summary

Il sistema z21-Terminal usa **DUE definizioni diverse** di "lead" e "rear":
1. **JMRI Consist Structure** - per funzioni DCC e YOLO detection
2. **Virtual Mode Compensation** - per speed matching automatico

**⚠️ CRITICAL**: I due sistemi hanno logiche **INVERTITE** intenzionalmente.

---

## 1. JMRI Consist Structure (Foundation)

### Definizione JMRI

**Lead Locomotive** = Locomotiva con **decoder sound** e **funzioni controllabili**
- Riceve comandi funzioni F0-F28 dal throttle
- Di solito ha luci, suoni, effetti speciali
- Fisicamente può essere davanti o dietro (irrilevante per JMRI)

**Rear Locomotive** = Locomotiva **senza sound** o con funzioni limitate
- Riceve solo comandi movimento (velocità, direzione)
- Non riceve funzioni (o solo F0 luci)
- Ruolo: fornire potenza motore

### Consist 11 (Tracciato Esterno - Ovale)

```
Lead:  Address 7 - E656 239 (Hornby TXS decoder 🔊)
Rear:  Address 8 - E444 056 (ESU LokPilot 5)

Consist DCC Address: 11
CV19 (lead): 11
CV19 (rear): 11
```

**Funzioni**:
- F0 → inviata a loco 7 + loco 8 (luci)
- F1-F28 → inviata SOLO a loco 7 (sound + effetti)

### Consist 10 (Tracciato Interno - Figura 8)

```
Lead:  Address 1 - Gr.675 017 (ESU LokSound V4.0 🔊)
Rear:  Address 5 - D645 014 (ESU LokPilot 5)

Consist DCC Address: 10
CV19 (lead): 10
CV19 (rear): 10
```

**Funzioni**:
- F0 → inviata a loco 1 + loco 5 (luci)
- F1-F28 → inviata SOLO a loco 1 (sound + effetti)

---

## 2. YOLO Detection Mapping

### Training Dataset

YOLO è stato addestrato usando la **nomenclatura JMRI**:

```python
YOLO_CLASSES = {
    0: '1_Gr675_017',   # Consist 10 LEAD (sound)
    1: '5_D645_014',    # Consist 10 REAR (no sound)
    2: '7_E656_239',    # Consist 11 LEAD (sound)
    3: '8_E444_056'     # Consist 11 REAR (no sound)
}
```

### Address-to-Class Mapping

**tracking_daemon.py**:
```python
ADDRESS_TO_CLASS = {
    1: 0,  # Gr.675 017 (Consist 10 LEAD)
    5: 1,  # D645 014 (Consist 10 REAR)
    7: 2,  # E656 239 (Consist 11 LEAD)
    8: 3   # E444 056 (Consist 11 REAR)
}
```

### Gate Tracking Detection

**Quando YOLO detecta una loco**:
1. Riconosce classe (0-3)
2. Mappa a DCC address (1,5,7,8)
3. Identifica consist (10 o 11)
4. Salva timestamp come **lead** o **rear** secondo `gate_config.json`

**gate_config.json** (DEVE matchare JMRI):
```json
"tracking_assignments": {
  "10": {
    "lead_address": 1,    // ← YOLO class 0
    "rear_address": 5,    // ← YOLO class 1
    "gate_ids": [3, 4]
  },
  "11": {
    "lead_address": 7,    // ← YOLO class 2
    "rear_address": 8,    // ← YOLO class 3
    "gate_ids": [1, 2]
  }
}
```

---

## 3. Cross-Gate Timing Calculation

### Formula Critica

**tracking_daemon.py - calculate_delta_t_centralized()**:
```python
# Check 1: Δt₁ = lead@G1 - rear@G2
lead_g1_ts = cdata['gate_timestamps']['lead'].get(g1)
rear_g2_ts = cdata['gate_timestamps']['rear'].get(g2)
delta_t1 = lead_g1_ts - rear_g2_ts

# Check 2: Δt₂ = lead@G2 - rear@G1
lead_g2_ts = cdata['gate_timestamps']['lead'].get(g2)
rear_g1_ts = cdata['gate_timestamps']['rear'].get(g1)
delta_t2 = lead_g2_ts - rear_g1_ts
```

### Interpretazione Δt

**Se gate sono sovrapposti** (posizione identica):
- **Δt < 0**: lead passa **prima** di rear (normale se lead è fisicamente davanti)
- **Δt ≈ 0**: perfettamente sincronizzati
- **Δt > 0**: rear passa **prima** di lead (anomalo se lead dovrebbe essere davanti)

**Se gate sono distanti** (cross-gate):
- Interpretazione più complessa
- Δt può essere positivo o negativo a seconda di chi attraversa quale gate per primo
- Cross-validation: |Δt₁ - Δt₂| dovrebbe essere piccolo se detection corretta

---

## 4. Virtual Mode Reference/Adjust Logic

### Il Problema di Speed Matching

**Consist 11 - Decoder instabili**:
- Loco 7 (E656, Hornby TXS): Decoder **instabile**, curva velocità irregolare
- Loco 8 (E444, ESU): Decoder **stabile**, curva velocità perfetta

**Consist 10 - Decoder da determinare**:
- Loco 1 (Gr.675, ESU LokSound): Da testare
- Loco 5 (D645, ESU LokPilot): Profilo Rivarossi standard (probabilmente stabile)

### Strategia Reference/Adjust

**Principio**: Mai toccare il decoder stabile, aggiusta sempre quello instabile.

**gate_config.json - reference_locos**:
```json
"reference_locos": {
  "11": {
    "reference": 8,  // ← Decoder ESU stabile (REAR in JMRI)
    "adjust": 7,     // ← Decoder Hornby instabile (LEAD in JMRI)
    "notes": "Loco 8 (ESU) stable - NEVER touch. Loco 7 (Hornby) always adjust"
  },
  "10": {
    "reference": 5,  // ← Probabilmente stabile (REAR in JMRI)
    "adjust": 1,     // ← Da confermare (LEAD in JMRI)
    "notes": "D645 014 (ESU) likely reference, Gr.675 017 (ESU LokSound) likely adjust"
  }
}
```

### ⚠️ INVERSIONE LOGICA

**JMRI Consist**:
- Consist 11: Lead=7, Rear=8
- Consist 10: Lead=1, Rear=5

**Virtual Mode**:
- Consist 11: Reference=8 (rear JMRI), Adjust=7 (lead JMRI)
- Consist 10: Reference=5 (rear JMRI), Adjust=1 (lead JMRI)

**Perché l'inversione?**
- JMRI sceglie "lead" per **funzioni sound** (criterio funzionale)
- Virtual Mode sceglie "reference" per **stabilità decoder** (criterio hardware)
- Nel tuo plastico: decoder sound (lead JMRI) sono quelli instabili!
- Risultato: lead JMRI = adjust Virtual Mode

---

## 5. Compensation Logic (Virtual Mode)

### z21_manager.py

**Quando Δt viene calcolato dal daemon**:
```python
if delta_t > 0:
    # Δt > 0: adjust loco passes AFTER reference (too slow) → SPEED UP
    speed_adjust_target = speed_adjust + compensation
else:
    # Δt < 0: adjust loco passes BEFORE reference (too fast) → SLOW DOWN
    speed_adjust_target = speed_adjust - compensation
```

### Esempio Consist 11

**Config**:
- Lead (JMRI): loco 7
- Rear (JMRI): loco 8
- Adjust (Virtual): loco 7
- Reference (Virtual): loco 8

**Gate sovrapposti G1 e G2**:
1. Loco 7 attraversa: `lead_timestamp = 10.0s`
2. Loco 8 attraversa: `rear_timestamp = 10.5s`

**Calcolo**:
```
delta_t = lead_timestamp - rear_timestamp
        = 10.0 - 10.5 = -0.5s
```

**Interpretazione**:
- Δt < 0 → loco 7 (adjust) passa PRIMA di loco 8 (reference)
- Loco 7 troppo veloce → **RALLENTA loco 7**

**Compensazione**:
```python
# delta_t = -0.5 (negativo)
speed_adjust_target = speed_adjust - compensation  // Rallenta
```

**Risultato**: ✅ Loco 7 rallentata, loco 8 mai toccata

---

## 6. Perché Invertire Config Rompe Tutto

### Scenario: Consist 10 con lead/rear invertito

**Config SBAGLIATO**:
```json
"10": {
  "lead_address": 5,  // ❌ INVERTITO
  "rear_address": 1   // ❌ INVERTITO
}
```

**YOLO detection**:
- Loco 1 detectata → salvata come `rear_timestamp` (SBAGLIATO!)
- Loco 5 detectata → salvata come `lead_timestamp` (SBAGLIATO!)

**Fisicamente sul plastico** (loco 1 davanti, loco 5 dietro):
1. Loco 1 attraversa per prima: `timestamp_loco1 = 10.0s`
2. Loco 5 attraversa dopo: `timestamp_loco5 = 10.5s`

**Calcolo con config invertito**:
```
delta_t = lead_timestamp - rear_timestamp
        = timestamp_loco5 - timestamp_loco1
        = 10.5 - 10.0 = +0.5s
```

**Interpretazione SBAGLIATA**:
- Δt > 0 → adjust loco passa DOPO (troppo lenta)
- Sistema pensa che loco 1 sia lenta → **ACCELERA loco 1**

**Realtà fisica**:
- Loco 1 è passata PER PRIMA (troppo veloce)
- Dovrebbe essere **RALLENTATA**, non accelerata!

**Risultato**: ❌ Compensazione **invertita** → desincronizzazione peggiora invece di migliorare

---

## 7. Gate Sovrapposti: Soluzione Semplice

### Problema Gate Distanti

**Consist 11** (ovale): Gate 1 e 2 abbastanza vicini, cross-gate timing funziona.

**Consist 10** (figura 8): Se gate troppo lontani, cross-gate confronta **giri diversi**.

Esempio log con gate distanti:
```
🚪 C10 Cross-gate: L5G4-L1G3 = Δt = +2.977s
```

Δt di 2.9s non ha senso per speed matching (gap troppo grande).

### Soluzione: Gate Sovrapposti

**Configurazione**:
```json
{
  "id": 3,
  "center": [1119, 183],
  "width": 100,
  "height": 100
},
{
  "id": 4,
  "center": [1119, 183],  // ← Stessa posizione!
  "width": 70,
  "height": 70
}
```

**Comportamento**:
- Lead attraversa → G3 e G4 trigger **contemporaneamente** (stesso frame)
- Rear attraversa → G3 e G4 trigger **contemporaneamente**

**Calcolo**:
```
Δt₁ = lead@G3 - rear@G4 = lead_ts - rear_ts
Δt₂ = lead@G4 - rear@G3 = lead_ts - rear_ts

→ Δt₁ = Δt₂ (identici!)
```

**Vantaggi**:
- ✅ Δt rappresenta il **vero gap lead-rear** (no dipendenza posizione gate)
- ✅ Cross-validation perfetta (Δt₁ = Δt₂ sempre)
- ✅ Funziona per qualsiasi tracciato (ovale, figura 8, etc.)
- ✅ Interpretazione chiara: Δt < 0 → lead passa prima (normale)

---

## 8. Testing e Troubleshooting

### Verifica Config Corretto

**Test 1: YOLO Model Classes**
```bash
cd ~/Documents/projects/z21-Terminal
python3 << EOF
from ultralytics import YOLO
model = YOLO('models/best.pt')
print('Class names:', model.names)
EOF
```

**Output atteso**:
```
{0: '1_Gr675_017', 1: '5_D645_014', 2: '7_E656_239', 3: '8_E444_056'}
       ↑ C10 lead      ↑ C10 rear      ↑ C11 lead      ↑ C11 rear
```

**Test 2: Startup Logs**
```bash
z21  # Lancia sistema
```

**Output atteso**:
```
🚂 Loaded 2 consists from config:
   Consist 10: lead=1 (class 0), rear=5 (class 1), gates=[3, 4]
   Consist 11: lead=7 (class 2), rear=8 (class 3), gates=[1, 2]
```

Se lead/rear non matchano YOLO classes → config invertito!

### Verifica Compensazione Corretta

**1. Attiva Virtual Mode** (per entrambe le loco):
```bash
# Via Web Dashboard: [⚙️ Consists] → Toggle Virtual Mode
# O manualmente via JMRI/z21 controller
```

**2. Osserva logs compensazione**:
```
🚪 C11 Cross-gate: L7G1-L8G2 = Δt = -0.234s
  🎚️ Compensation: Δt=-0.234s (SYNCED), slow down loco 7 by 2 steps
```

**3. Verifica logica**:
- Δt < 0 → adjust passa prima → **slow down adjust** ✅
- Δt > 0 → adjust passa dopo → **speed up adjust** ✅

Se compensazione va nella direzione opposta → config lead/rear invertito!

---

## 9. Quick Reference

### Consist 10 (Tracciato Interno - Figura 8)

| Ruolo | Address | Loco | Decoder | YOLO Class |
|-------|---------|------|---------|------------|
| **JMRI Lead** | 1 | Gr.675 017 | ESU LokSound V4.0 🔊 | 0 |
| **JMRI Rear** | 5 | D645 014 | ESU LokPilot 5 | 1 |
| **Virtual Adjust** | 1 | (same) | Instabile (da confermare) | 0 |
| **Virtual Reference** | 5 | (same) | Stabile (probabile) | 1 |

**Gate**: G3 e G4 sovrapposti a [1119, 183]

### Consist 11 (Tracciato Esterno - Ovale)

| Ruolo | Address | Loco | Decoder | YOLO Class |
|-------|---------|------|---------|------------|
| **JMRI Lead** | 7 | E656 239 | Hornby TXS 🔊 | 2 |
| **JMRI Rear** | 8 | E444 056 | ESU LokPilot 5 | 3 |
| **Virtual Adjust** | 7 | (same) | Instabile (confermato) | 2 |
| **Virtual Reference** | 8 | (same) | Stabile (confermato) | 3 |

**Gate**: G1 [1227, 213] e G2 [141, 162] (abbastanza vicini)

---

## 10. Decisioni di Design

### Perché Due Sezioni Separate nel Config?

**tracking_assignments** (JMRI structure):
- Usata da YOLO detection per mappare classes → addresses
- DEVE matchare il training dataset YOLO
- Cambiare questa rompe la detection (YOLO cerca classe 0 per loco 1)

**reference_locos** (Virtual Mode strategy):
- Usata da compensation logic per decidere quale loco aggiustare
- Indipendente da JMRI (basata su stabilità hardware)
- Invertita rispetto a JMRI per il tuo plastico

**Alternativa scartata**: Usare una sola sezione con flag "is_reference"
- Pro: meno duplicazione
- Contro: confonde i due concetti (JMRI vs Virtual Mode)
- Scelta: separare per chiarezza semantica

### Perché Gate Sovrapposti Opzionali?

**Consist 11**: Gate separati funzionano (tracciato ovale semplice)

**Consist 10**: Gate sovrapposti necessari (tracciato figura 8 complesso)

**Flessibilità**: Sistema supporta entrambi approcci.

---

## 11. Future Improvements

### Auto-Detect Lead/Rear Order

Possibile enhancement: rilevare automaticamente ordine fisico lead/rear sul plastico.

**Algoritmo proposto**:
1. Utente posiziona loco ferme in ordine noto
2. Sistema detecta entrambe con YOLO
3. Compara coordinate (x, y)
4. Determina chi è davanti/dietro geometricamente
5. Valida contro config e avvisa se invertito

**Pro**: Elimina errori configurazione manuale
**Contro**: Richiede calibrazione iniziale, sensibile a posizione camera

**Status**: Non implementato (priorità bassa)

---

## Glossary

- **Lead (JMRI)**: Locomotiva con sound e funzioni controllabili
- **Rear (JMRI)**: Locomotiva senza sound (o funzioni limitate)
- **Reference (Virtual)**: Locomotiva con decoder stabile (mai toccata da compensation)
- **Adjust (Virtual)**: Locomotiva con decoder instabile (compensata per matchare reference)
- **Cross-gate timing**: Confronto timestamp di loco diverse in gate diversi
- **Gate sovrapposti**: Due gate configurati alla stessa posizione fisica

---

**End of Document**
