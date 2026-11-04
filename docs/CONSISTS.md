# Consists

Active assignments live in `config.json` (`consists`). This page records what is
current and what to restore, because the `notes` field is not shown by the UI.

## Current

| Consist | Lead | Rear | Reference (gate) | Adjust (gate) | Threshold |
| --- | --- | --- | --- | --- | --- |
| 10 C10 Interno | 6 D445 1140 | 5 D645 014 | 5 (G3) | 6 (G4) | 5 |
| 11 C11 Esterno | 7 E656 239 | 8 E444 056 | 8 | 7 | 10 |

Consist 10 runs on 6+5 only while loco 1 (Gr.675 017) is under repair, for tests
and for demos run from the gaming PC.

## Consist 10 history

- **Original, to restore**: lead 1 Gr.675 017, rear 5 D645 014, reference 5 at
  gate 3, adjust 1 at gate 4, threshold 5.
- **Placeholder** (`fe6a32d`): lead 1 + rear 4 (`2048 010-9`, loco not on the
  layout, dead track) - deliberate safety, a wrong command hits no motor, and
  the tracker skips the consist.
- **Current**: lead 6 D445 1140 + rear 5 D645 014, same gates and threshold.

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
