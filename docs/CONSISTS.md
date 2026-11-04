# Consists

Active assignments live in `config.json` (`consists`). This page records what is
current and what to restore, because the `notes` field is not shown by the UI.

## Current

| Consist | Lead | Rear | Reference (gate) | Adjust (gate) | Threshold |
| --- | --- | --- | --- | --- | --- |
| 10 C10 Interno | 1 Gr.675 017 | 4 2048 010-9 | 4 | 1 | 5 |
| 11 C11 Esterno | 7 E656 239 | 8 E444 056 | 8 | 7 | 10 |

While loco 1 is under repair, consist 10 is deliberately a **phantom** pair:
neither of its locos is on the layout. Two effects, both wanted:

- `backend/tracking/yolo_tracker.py` skips a consist whose locos are not in the
  YOLO class set (`CLASS_NAMES` covers 1, 5, 7, 8), so consist 10 is not
  tracked. `Skipping consist 10: rear loco 4 not in YOLO training set` in the
  log is expected.
- The two locos on the track, **5 D645 014** and **6 D445 1140**, belong to no
  consist, so they keep speed and direction: a loco flagged `in_consist` is
  limited to functions in the UI (`ConsistController.jsx:405`; the flag comes
  from `roster_loader.py`). Putting 5 and 6 in consist 10 would disable the
  very control those panels exist for.

Drive them with their own UI panels, or with the `z21-terminal` CLI
(`scripts/z21_controller.py`), which is quicker for single locos.

Loco 6 has no YOLO class, so it can never be recognised; giving it one means
retraining (`docs/JEV_INTEGRATION_ANALYSIS.md`, section 3).

## Consist 10 history

- **Original, to restore**: lead 1 Gr.675 017, rear 5 D645 014, reference 5 at
  gate 3, adjust 1 at gate 4, threshold 5.
- **Placeholder** (`e087f8e`): lead 1 + rear 2.
- **Phantom, current** (`fe6a32d`): lead 1 + rear 4 (`2048 010-9`, loco not on
  the layout, dead track).

Geometry: figure-8, only the gate 3 / gate 4 pairing is valid for consist 10
(asymmetric gates, fewer crossings per lap, hence threshold 5).

Consist 11 is symmetric: both L7@G1-L8@G2 and L7@G2-L8@G1 are valid (oval
track), threshold 10.

## Restore consist 10

1. In the UI or `config.json`: lead 1, rear 5, reference 5, adjust 1 (gates 3/4,
   threshold 5).
2. Update `notes` in `config.json` so 1+5 reads as current.
3. Commit, push, deploy: `git push origin develop`, then
   `ssh riccardo@gaming-pc "cd C:\z21-Terminal && git pull && z21-restart"`.
