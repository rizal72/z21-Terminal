# Jev integration analysis

> Analysis only — nothing was applied, installed or changed. Written 2026-09-21.
> Scope: whether TypeSafe **Jev** (System One) has a place in Z21, and what the
> identity architecture costs today.
>
> **Status: parked for a future decision.** Read this before proposing anything
> that touches the CV pipeline, the YOLO class set, or the roster sync.
>
> **Revised 2026-09-21**, after the owner clarified the layout (§2.1). The first
> draft assumed consist attribution could fall back on position and order; with
> four locomotives always in frame and a tunnel blind spot, it cannot. See §7 B.
>
> **Update 2026-11-04**: consist 10 is deliberately the phantom pair lead 1 +
> rear 4 while loco 1 is under repair, so the tracker skips it by design and no
> Δt is measured for it. The locos on the track, 5 D645 014 and 6 D445 1140, run
> individually (UI panels, or the `z21-terminal` CLI). Loco 6 is not in
> `CLASS_NAMES` and can never be recognised, so any identity work for it means
> retraining, as §3 describes. The "reference loco 5, adjust loco 1" statement
> in §2 is the original mapping to restore, not the current one.

Related: `docs/COMPUTER_VISION.md` (the CV system), `docs/LOCOMOTIVE_SYNC_MAC_PC.md`
(roster sync), `backend/tracking/yolo_tracker.py` (identity lives here).

---

## 1. Summary of the verdict

1. **Jev cannot take part in the recognition loop.** It is text-only by
   contract. No prompt engineering changes that.
2. **Jev does not remove the retraining cost.** That cost has an architectural
   cause (identity is baked into the detector's class names) and an
   architectural cure, described in §7 — which does not involve Jev at all.
3. **Jev's defensible uses are the decision layers around the CV**, where
   judgement is currently hand-written: detection-sequence plausibility, the
   CV-adjustment policy, diagnostic triage. Plus one case that is not in the CV
   path at all: **roster identity matching** (`entity_alignment`), which is the
   best-supported pattern in Jev's own documentation and the only one whose
   ground truth already exists here.
4. **Jev is a cloud call at runtime.** Z21 is on-prem by design; today the only
   cloud touchpoint is offline training. Any runtime use, and especially one
   adjacent to a path that writes CVs on moving locomotives, is a policy
   decision, not a technical detail.

---

## 2. What the CV system does today (verified)

The system does **not** perform open-set recognition. It measures the
**synchronisation error (Δt)** between the two locomotives of a consist as they
cross fixed gates.

| Stage | Implementation | Evidence |
|---|---|---|
| Capture | Tapo IP camera over RTSP | `backend/tracking/rtsp_handler.py:57`, `:18` (`rtsp_transport;tcp\|stimeout;5000000`) |
| Detection | **YOLOv8n-OBB**, ultralytics, single stage | `yolo_tracker.py:207` — `YOLO(str(engine_path), task='obb' if yolo_obb else 'detect')` |
| Artifacts | `scripts/models/`: `best_obb.pt/.onnx/.mlpackage`, `best.pt` (+ `.engine`) | load priority `.engine > .mlpackage > .onnx > .pt` — `yolo_tracker.py:174` |
| Thresholds | `yolo_confidence: 0.4`, `yolo_iou: 0.6`, `yolo_imgsz: 640`, `yolo_obb: true` | `config.json` |
| **Identity** | **the detector class name *is* the identity** | `yolo_tracker.py:27-33` — `CLASS_NAMES = {0: '1_Gr675_017', 1: '5_D645_014', 2: '7_E656_239', 3: '8_E444_056'}` |
| Class→address | hardcoded dict | `yolo_tracker.py:34-41` — `ADDRESS_TO_CLASS = {1: 0, 5: 1, 7: 2, 8: 3}` |
| Second visual stage | **none.** Zero code hits for OCR / UIC / embedding / template matching | project-wide search |
| Association | gate-crossing timestamps → Δt → SQLite | `yolo_tracker.py:706` `_update_gate_timing`, `:501` `calculate_delta_t_centralized`, `backend/services/data_db.py` |
| Consist source | `config.json` + JMRI `consist.xml` — not vision | `backend/roster_loader.py:20-24`; gates e.g. `gate_ids: [1, 2]` |
| Actuation | Operations Mode CV write, XpressNet `0xE6 0x30` | `backend/z21_manager.py`, `scripts/z21.py`, `write_cv_ops_mode()` |

### 2.1 Layout and tracking model

Stated by the owner (2026-09-21) — authoritative for the physical layout:

- **One camera, one frame, the whole layout.** Not a camera per gate.
- **Two tracks**: an outer oval, and an inner track that is part oval, then a
  figure-8, then back — so it is longer. They run parallel in places, and the
  figure-8 crosses itself.
- **Exactly 4 locomotives**, 2 per consist, **all running simultaneously and
  always in frame**. The design goal is that all four are recognised at the same
  time, each with its own coloured box (visible in debug mode).
- The roster size is stable; individual locomotives get swapped.

From the code and `docs/TRACK_MAP_IMPLEMENTATION.md`:

- The camera is an **oblique view from the right, 1280x720**; the backend applies
  a **perspective correction** (`cv2.getPerspectiveTransform()`, the four layout
  corners → a 600x1200 rectangle, **6 px/cm**), so the frontend works on a
  top-down plane. Single source of truth: the transform lives in
  `backend/main.py`.
- Track paths are modelled as **outer oval + inner figure-8**; gates **G1-G4**
  are geometry on that plane, assigned per consist via `gate_ids`.
- **The tunnel is a ~5 s blind spot for consist 10.** The frontend hook
  (`useLocomotivePositions.js`) does tunnel entry/exit detection, **linear
  interpolation** across the blind spot, and **re-association logic** — so
  re-acquiring identity after the tunnel is an acknowledged weak point in the
  design, not an exotic edge case.

Consequence: **identity is required continuously, per frame, for four
simultaneous objects**, on tracks that run adjacent with one crossing itself and
with a blind spot that has to be resolved. That is what the YOLO class is really
providing, and why it cannot simply be replaced by geometry — see §7.

**Modes** (`docs/COMPUTER_VISION.md:178`): `Monitor Only` (operator decides),
`Auto CV Adjust` (writes CVs while circulating; safety: max ±5 adjust/session,
30 s cooldown, confirmation UI; cadence 1 step per 5 min / 2 min / 30 s),
`Software Sync` (no CV writes).

**Reference Loco Strategy** (`docs/COMPUTER_VISION.md:102`) — the adjustment
policy is a hand-written judgement, already: consist 11 → *"Mai toccare i CV
della loco 8"* (ESU LokPilot 5, stable), always adjust loco 7 (Hornby TXS,
unstable); consist 10 → reference loco 5 (ESU LokPilot 5), adjust loco 1
(Gr.675 017). Direction from the sign of Δt.

**Scale**: 4 classes in the model, **9 roster entries** (2 consists + 7
locomotives), `config.json:160` `"locomotives"` metadata, JMRI roster XML
fallback.

**Discrepancy to settle**: the doc proposes Δt thresholds baseline ≈ 0 /
warning 0.5 / critical 1.0 / emergency 2.0 s, while `config.json`
`timing_thresholds` carries **warning 1 / critical 1.5**. The doc and the live
config disagree; whatever policy is built on top must be fed the real values.

---

## 3. Why adding a locomotive costs a full retrain

The cause is structural, and the project documents it against itself:

- `docs/COMPUTER_VISION.md:158` — *"YOLO impara i nomi delle classi durante
  training (embedded in `best.pt`) … il codice mappa class ID → DCC address
  tramite il prefisso"*.
- `docs/COMPUTER_VISION.md:160` — *"REGOLA ASSOLUTA: ❌ MAI cambiare DCC address
  (CV1) dopo training YOLO"*; a CV1 change costs *"Re-training completo da zero"*
  → *"⏱️ Tempo totale: ~2-3 ore lavoro"* (`:167`, `:172`).
- `docs/COMPUTER_VISION.md:1384` — *"NEVER change locomotive DCC addresses after
  training — breaks class mapping, requires full re-training"*.
- `docs/COMPUTER_VISION.md:1295` — *"⚠️ CRITICAL: DCC Address Class Mapping … in
  code: `DCC_TO_YOLO_CLASS = {1: 0, 5: 1, 7: 2, 8: 3}`"*.
- Dataset cost (`:1221-1223`): *"50-100 foto annotate (minimo assoluto) / 200-300
  foto annotate (raccomandato)"*; Phase 3A *"1-2 ore"* (`:1073`); the cycle is
  record video → extract frames → **annotate on Roboflow** → **train on Google
  Colab** → deploy symlink (`scripts/utils/README.md`).
- `docs/COMPUTER_VISION.md:1069` — *"❌ Richiede training custom (200-300 foto
  annotate)"*.

So the recurring cost is **data acquisition and annotation**, not compute. And
the address freeze is a consequence: identity, address and class name are one
single thing.

**Where the cost actually sits** — `docs/CONSIST_TRACKING.md` § *How to Add New
Consist/Locomotive* makes the split explicit:

- Adding a **consist**, or wiring gates to one, is **config plus a restart**:
  *"Step 3: Restart daemon → **DONE!** Gate timing now active for Consist 10."*
- Adding a **locomotive** is the expensive path, and the prerequisites are
  listed in order: *"1. Train YOLO model with loco 3 and 4 images. 2. Update
  `CLASS_NAMES` and `ADDRESS_TO_CLASS` in tracking_daemon.py. 3. Deploy new YOLO
  model"* — *"Then: Just add config → restart → works!"*.

So the config layer is already generic (the Phase 5 refactor removed the
hardcoded per-consist code). **The retraining is coupled to locomotives and to
nothing else** — which is exactly where the pain is felt.

**Documented weaknesses of the current detector** (these matter for §5):
- `docs/CHANGELOG_ARCHIVE.md:1076`, `:1086` — training bias: more large/close
  locomotives in the dataset *"sacrifices small/distant"* detection.
- `docs/CHANGELOG_ARCHIVE.md:1050` — *"False positives (wagons misclassified,
  double bbox)"*.

**A second, independent pain**: `docs/LOCOMOTIVE_SYNC_MAC_PC.md:11` — *"Adding
new locomotives requires manual coordination between Mac (JMRI) and PC
(production)"*; `:50` — *"❌ Manual file copying (error-prone)"*. Nothing to do
with vision, and nobody has solved it.

**Constraints** (matter for where anything may run): on-prem by design
(`README.md:66-67`); the only cloud touchpoint is training on Google Colab
(`COMPUTER_VISION.md:1219`); inference on CPU is acceptable on a Mac (`:1216`),
GPU needed for TensorRT (`:1377`); measured frame cost `.pt` ~30 ms, `.onnx`
~15-20 ms, `.engine` ~6-15 ms, gate timing < 100 ms (`:1346-1352`); Windows
deployment via `start-backend.ps1` (Task Scheduler, uvicorn :8000).

---

## 4. What Jev is, and what it is not (verified)

**Text only.** `docs.typesafe.ai/concepts/system-one.md`: *"Jev currently accepts
text input only. It evaluates strings, JSON objects, and arrays of text.
Images, audio, and video are not supported (yet)."* The Doom demo runs *"on
structured state as a data structure with text, not on images (yet…)"*.

| | |
|---|---|
| Question types | `noul` (yes/no, 0-1), `choice` (**max 255 options**, each with a rubric), `score` (2-10 levels) |
| Output | `choice` + `probabilities` (full distribution, sums to 1) + **`confidence`** (concentration of the distribution). **`noul` carries no confidence** |
| Input | free text or structured state (object/array) — examples may be embedded in `state`; criteria are supplied as a JSON map of option → rubric |
| Limits | 64k tokens/request; 32k for `state` + longest question; rate limits 250k tok/s, 1200 req/min |
| Latency | documented 70-500 ms end-to-end |
| Cost | **$0.042 / Mtok input, output free.** A ~4,300-token decision ≈ $0.0002; 1,000 decisions ≈ **$0.18** |
| Extraction | not free-form: it **selects among candidates your code pre-parses** |
| Matching | set membership over **explicit** candidates — **no embedding / vector similarity** |
| Abstention | code-side: compare `confidence` to a threshold; docs prescribe *"Low confidence: Do not act. Route to a human"* |

Their own published caveat, worth remembering: *"We can't prove it isn't
subsidized."*

Relevant documented patterns (`docs.typesafe.ai/llms.txt`): intent routing, the
classification-with-confidence pattern, reranking a shortlist,
`pre_parsed_value_extraction`, `citation_check`, `consistency_noul`,
`llm_guardrails`, and **`entity_alignment`** — *"Decides which of 450 candidate
pairs… describe the same product… no threshold to fit"*.

---

## 5. Use cases, ranked by defensibility

| # | Use case | Primitive | What it replaces | Constraint |
|---|---|---|---|---|
| 1 | **Roster identity matching** — is this JMRI entry the same locomotive as this production entry? | `entity_alignment` (`choice` over pairs) | *"manual file copying (error-prone)"* | none in the CV path; **ground truth already exists** |
| 2 | **Ambiguity resolution / re-association** — after the tunnel blind spot or a crossing, decide which blob is which address | `choice` over the candidate assignments (**not `noul`**: no confidence) | the current linear interpolation across the ~5 s tunnel blind spot, and the documented *"wagons misclassified, double bbox"* (`CHANGELOG_ARCHIVE.md:1050`) | invoked **on exception**, a few times per lap — see the latency note below; candidates and evidence must be serialised |
| 3 | **CV-adjustment policy** — which CV, which direction, how much, or abstain, from decoder facts + Δt history | `choice` over a closed action set | the hand-written *"mai toccare la 8"* rules and the 5/2/0.5 min ladders | decoder-agnostic: a new locomotive is **its facts in the request, no retraining** — but it is adjacent to a write path, so the deterministic controller must keep authority |
| 4 | **Diagnostic triage** — Δt does not converge → closed set of causes → remedy | `choice` over causes | the C11 case, where the speed table was tuned *step-by-step a mano* | the cause set must be closed and written by us |
| 5 | **Operator text → entity/action** | extraction (pre-parsed candidates) | lookup by hand | the candidate list must be produced by our code |

**Latency rules out the control loop**: frames are 6-15 ms with the TensorRT
engine; Jev answers in 70-500 ms. It may sit at **event** granularity (a gate
crossing, an adjustment decision, an operator query) — never per frame. The CV
adjustment cadence (30 s to 5 min) is comfortably slower than Jev, which is why
case 3 is technically feasible at all.

---

## 6. The case worth testing first: roster alignment

Why this one:

- `entity_alignment` is a **documented pattern with a worked example** — the
  lowest-risk adoption path in the whole catalogue.
- The **ground truth exists today**: the owner knows which entries are the same
  locomotive.
- It is **offline**: no camera, no layout, no CV write path, no serialisation work.
- It attacks a pain that is documented and persistent
  (`LOCOMOTIVE_SYNC_MAC_PC.md:11`, `:50`).

Proposed shape: freeze a set of pairs (matching *and* deliberately
non-matching, including near-misses such as two locomotives of the same class
with different addresses), run them through a `choice`/`entity_alignment` call,
and measure accuracy and the confidence distribution. **Success criterion to
be agreed before the run**, because the honest question is not "does it work"
but "does it beat the deterministic comparison of the fields we already have".

---

## 7. The architectural question (parked, deliberately)

This is independent of Jev and probably worth more. The retraining cost exists
because **identity is the detector's class set**: a closed set, with the DCC
address embedded in the class name and frozen once trained.

Note what that class is actually doing, given the layout in §2.1: with four
locomotives moving at once, two tracks running adjacent in places and one
crossing itself, and a ~5 s blind spot inside the tunnel, the class **is the
per-frame re-identification from appearance**. That work is not redundant — it
is what keeps the four objects apart at the moments tracking alone cannot.
So the question is not "how do we delete the classes" but **"how do we get the
same per-frame identity without a retrain per locomotive"**.

### Options

**A. Keep the per-frame identity, change where it comes from — appearance
gallery instead of class names.**
The detector emits a generic (or coarse) class plus geometry; identity comes
from an **appearance embedding + gallery**: enrolling a locomotive means
**N reference photos, no retraining**, and identity is the best match in the
gallery, with a confidence and a no-decision path back to the operator.

- Removes: the 50-300 annotated photos per locomotive, the Roboflow/Colab cycle,
  and the CV1 freeze (the address becomes a runtime attribute rather than
  something baked into `best.pt`). **A roster swap becomes minutes of enrolment
  instead of ~2-3 hours of retraining.**
- **The crux, to test first**: can a small local encoder separate *these*
  locomotives at *this* scale and angle? The layout is imaged obliquely at
  1280x720 and the corrected plane is 6 px/cm (§2.1), while the project already
  documents a bias that *"sacrifices small/distant"* detection
  (`docs/CHANGELOG_ARCHIVE.md:1076`). Crop the oriented box, rectify it with the
  existing perspective transform, and measure separability on held-out frames —
  before designing anything else.
- Requires: a local encoder, a gallery store, a matcher, and a fallback for when
  the gallery cannot decide.

**B. Drop the identity classes, keep the geometry — excluded by this layout.**
The first draft of this document assumed consist attribution could fall back on
position and order. It cannot: **four locomotives are always in frame**, on two
tracks that run parallel in places, one of which crosses itself, with a ~5 s
blind spot in the tunnel — and the consist definitions are *by address*
(`lead_address` / `rear_address`). Geometry and order alone cannot hold a 4-way
correspondence through a crossing or a blind spot. B is live only if the
operational model changes, e.g. one consist on the layout at a time.

**C. Use what the command station already knows — as a prior.**
The z21 knows which addresses it is driving and at what speed. After the tunnel
the current frontend logic interpolates **linearly** for ~5 s; a speed-aware
prediction is strictly better, and a predicted position is exactly what
disambiguates re-entry. Cheap, deterministic, no new model, and measurable
against today's behaviour. Combine with A or D.

**D. Hybrid**: generic detector class + re-id gallery for the ambiguous cases
only, keeping the deterministic path as the fast lane.

### What is *not* on the table

Jev is not a component of A-D. It has no visual input and no vector similarity;
it cannot be the identity layer. Any proposal that puts it there is
misunderstanding the tool.

### To settle before designing any of this

- **How often does the roster actually change?** The value of A is proportional
  to locomotive swaps per year — that is the entire ROI calculation.
- **Can the z21's known speeds replace the linear tunnel interpolation?**
  (Option C.) Measurable against today's behaviour, no model involved.
- **How often does re-association actually fail today?** If it is rare, the
  ambiguity path (§5 case 2) has little to buy.
- The size of a locomotive on the corrected plane, and separability between
  classes at that size — the input to the test in A.

---

## 8. Verification plan (zero risk, no layout needed)

**Experiment 1 — roster alignment** (§6). Offline, ground truth present,
documented pattern. Decide the success criterion first.

**Experiment 2 — CV decision replay.** Take a recorded session: detection
sequence, Δt series, decoder facts, and the adjustments the deterministic policy
actually made. Ask Jev for its decision on the same inputs and compare. No write
path is touched, no camera is needed.

**Prerequisite for experiment 2**: the detection sequence does not exist as a
text artifact today — it must be serialised. That is real work in our code, and
it is the hidden cost of every use case in §5 except number 1.

The question both experiments must answer is the same, and it is the only one
that matters: **does it add anything the existing rules do not already do?**
The rules work today. Without a measurement, adopting this would be a bet.

---

## 9. Open questions

- Real Δt thresholds: the config (1 / 1.5) and the doc (0.5 / 1.0 / 2.0)
  disagree — decide which is authoritative.
- Does `analytics.db` already hold anything usable as a decision log (per-loco
  identity or adjustment history) that experiment 2 could reuse?
- Actual class count inside the shipped `best_obb.pt` — 4 documented, not
  inspected from the binary.
- Does the JMRI↔production roster drift only in names, or also in
  addresses/decoders? It changes what `entity_alignment` is being asked.
- `docs/CONSIST_MAPPING.md` states that the JMRI "lead/rear" definitions and
  the compensation "reference/adjust" ones are **deliberately inverted**
  (*"I due sistemi hanno logiche **INVERTITE** intenzionalmente"*). Any policy
  built on top — Jev's included — must respect that convention, or it will slow
  the wrong locomotive.

---

## 10. Sources and evidence

**Z21, read only (2026-09-21)**: `docs/COMPUTER_VISION.md` (§ Approach, Reference
Loco Strategy, DCC Address as YOLO Class Prefix, Modes, TensorRT, latency
tables), `docs/CHANGELOG_ARCHIVE.md`, `docs/LOCOMOTIVE_SYNC_MAC_PC.md`,
`docs/TRACK_MAP_IMPLEMENTATION.md` (perspective correction, track paths, tunnel),
`docs/CONSIST_TRACKING.md` (§ How to Add New Consist/Locomotive),
`docs/CONSIST_MAPPING.md` (lead/rear vs reference/adjust),
`README_CAMERA.md`, `config.json`, `backend/tracking/yolo_tracker.py`,
`backend/tracking/rtsp_handler.py`, `backend/roster_loader.py`,
`backend/services/data_db.py`, `backend/z21_manager.py`, `scripts/`,
`scripts/utils/README.md`, `start-backend.ps1`.

**Jev / TypeSafe**: `docs.typesafe.ai/concepts/system-one.md`,
`docs.typesafe.ai/concepts/state.md`, `docs.typesafe.ai/models.md`,
`docs.typesafe.ai/api.md`, `docs.typesafe.ai/confidence.md`,
`docs.typesafe.ai/patterns/confidence-routing.md`, `llms.txt` cookbook index
(including `entity_alignment.md`, `consistency_noul_cookbook.md`,
`pre_parsed_value_extraction_cookbook.md`), and the System One announcement post.

**Unverified**: numeric latency is a vendor claim (our own probes measured
p50 ≈ 309 ms on the direct endpoint, ≈ 616 ms via the OpenCode gateway, and
≈ 4,300 input tokens per generation — measured for a different task shape, so
treat as indicative); `confidence` calibration methodology is not published;
whether `state` examples behave as real few-shot conditioning; behaviour above
255 options.
