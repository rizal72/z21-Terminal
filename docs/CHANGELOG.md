# Changelog

Active changelog for recent changes. Entries older than ~30 days are moved to
[CHANGELOG_ARCHIVE.md](CHANGELOG_ARCHIVE.md).

---

## 2026-09-10 — CoreML loader for Mac ANE inference (`988886c`, `34d2d01`)

### Feature
- **CoreML loader** in `backend/tracking/yolo_tracker.py`: model selection chain is now
  `.engine` (TensorRT) > `.mlpackage` (CoreML) > `.onnx` > `.pt` (PyTorch). The CoreML
  branch sits between TensorRT and ONNX and follows the same try/except + log pattern
  as the sibling branches, with explicit `task='obb'`/`'detect'` (CoreML does not
  preserve task metadata, same as TensorRT/ONNX).
- On the Mac, `best_obb.mlpackage` now wins over `.onnx` (Apple ANE beats ONNX);
  PC behavior unchanged (no `.mlpackage` exists there, TensorRT engine wins).
- `coremltools>=6.0` added to `scripts/requirements.txt`.

### Review (APPROVED)
- P2 fixed: CoreML-failure fallback log now says "Falling back to ONNX/PyTorch models..."
  (was "PyTorch", but ONNX is the next branch tried).
- P3 informational: ultralytics 8.4 loads non-.pt backends lazily — `YOLO()` stores only
  the path, real backend instantiation happens at first predict. The constructor
  try/except therefore cannot catch CoreML load failures (pre-existing pattern shared
  with the engine/ONNX branches).
- Known pyright errors in the file (lines 168, 244, 404, 438) are pre-existing baseline.

### Git / policy
- `*.mlpackage` added to `.gitignore` and untracked (regenerable export, same policy
  as `*.onnx`/`*.engine`; `.pt` weights stay tracked). The 6 MB bundle briefly tracked
  in `988886c` remains in git history (no history rewrite).

### Verification
- Smoke test on Mac M5 (ultralytics 8.4.146 + coremltools 9.0): tracker auto-selects
  `best_obb.mlpackage` with `task='obb'`, OBB inference works (black frame → 0 detections).
- Not yet done: end-to-end smoke with the real RTSP camera — compare CoreML detections
  (classes/confidences/orientation) vs PC TensorRT.

---

## 2026-09-10 — Docs genericization (`8a5b17c`, cleanup pass)

- **CLAUDE references cleanup (stratum A - living instructions)**: deployment skill
  (`.claude/skills/z21-deployment/SKILL.md`, untracked) fully genericized — "Claude" →
  "the AI agent", "CLAUDE.md Management Policy" → CHANGELOG policy, docs-only deploy
  tree now cites `AGENTS.md`/`docs/*`; OK-to-commit list updated (AGENTS.md untracked).
- Tracked docs: `docs/Z21_PROTOCOL.md`, `docs/JMRI_INTEGRATION.md` dead pointers
  ("see main CLAUDE.md") → `AGENTS.md`; `scripts/release/bump_version.py` docstring
  no longer mentions CLAUDE.md; `test/memory/` instructions say "your AI coding agent".
- Intentionally left: historical/archeological docs (CHANGELOG_ARCHIVE.md,
  DB_REFACTORING.md, REFACTOR_PLAN.md, SPEED_TABLE_DB_MIGRATION.md, etc.),
  author attributions, `.gitignore` entries (`.claude/`, `CLAUDE.md`).


---

## 2026-09-10 — Tailscale doc corrections

- `docs/GPU_DEPLOYMENT.md`: fixed self-contradiction in "Differenza Mac vs PC" — Mac
  DOES use `tailscale serve` for HTTPS dashboard (documented commands: 443 → Vite 5173,
  optional :8000 API); PC block restored. Section header updated ("in uso su PC e Mac").
- Evidence: `web/vite.config.js` allowlists the Mac `*.ts.net` hostname (only needed
  when Vite is reached via tailscale serve).
- `AGENTS.md` (local, untracked): "Mac Dev (Tailscale)" URL now points to
  `mbp14diriccardo` (current dev Mac); old `mbp16diriccardo` noted as retired.

### Config — consist 10 placeholder locos (INTENTIONAL safety)
- Consist 10 now uses **lead 1 + rear 4** (commit `fe6a32d`): rear loco 4 is a
  NON-EXISTENT loco. Deliberate choice: while loco 1 is under repair, its position
  (dead track) makes accidental consist-11/10 mixups harmless — wrong commands hit
  no motor. Side effect (also desired): tracker skips consist 10 ("loco not in YOLO
  training set" warning is expected).
- Original mapping to restore after loco 1 repair: **lead 1 + rear 5**
  (reference 5, adjust 1) — see commit `e087f8e` for the history: original 1+5 →
  placeholder 1+2 (`e087f8e`) → dead loco 1+4 (`fe6a32d`).

---

## 2026-08-27

### Bug fixes
- **Reference compensation notification** (`41cb352`): when the reference is reduced
  (overflow: adjust already at 126) the notification "Loco X (ref): Speed -Y%" now
  appears — previously silent.
- **Phase 1 video hardening** (`f5d9f0d`): RTSP TCP + stimeout, frame None guard,
  reconnection backoff, daemon watchdog, faulthandler → decode errors 108→0,
  disconnections 106→4.
- **Stale state after consist CRUD** (`c4226a4`): in-place mutation of the shared dict
  (broadcast/WS/main) + z21_manager reconciliation → UI updates live without z21-restart.
- **Delta-t Panel button active state** (`2cd478e`): video panel toolbar's "Delta-t
  Panel" button now shows the pressed/active state (mirrors Debug/Edit pattern) —
  previously it had static styling and never reflected the open panel.

### Infrastructure
- **TensorRT OBB regenerated**: `best_obb.engine` was lost (untracked from git, local
  file not regenerated) → model ran on ONNX → FPS drop. Re-exported on PC → TensorRT active.
- **Mac venv restored**: Python 3.11.16 (was broken, symlink to non-existent python@3.11).

### Config / data
- **Temporary C10 config**: loco 1+2 placeholder (loco 5 freed, used separately with loco 6).
- **JMRI → z21 DB sync**: loco 6 synced (loco 5 already correct); procedure in
  "JMRI → z21 DB Sync" section of AGENTS.md.
- **JMRI sync script idea** in `docs/FUTURE_IDEAS.md` (SSH variant).

