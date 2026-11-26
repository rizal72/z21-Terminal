# Documentation

`docs/` holds what is true now, or the entry point to it. `docs/archive/` holds what happened: plans
already executed, refactors, migrations, audits. An archived file is memory, not instructions, and its
first line says so.

## Start here

- `../README.md`, what the project is and how to run it.
- `DATABASE_POSTGRES.md`, where the database lives, how it is backed up, what happens when it is down.
- The configuration lives in that database too: gates, consists, locomotives and thresholds, one
  document shared by every host. `config.seed.json` is only the seed. Also in `DATABASE_POSTGRES.md`,
  "Configuration".

## Reference

| file | subject |
|---|---|
| `DATABASE_SCHEMA.md` | tables, types and indexes of the analytics database |
| `ANALYTICS.md` | events, sessions, dashboard data and how it is computed |
| `REPORTS_TAB.md` | reports view |
| `WEB_DASHBOARD.md` | dashboard, ports and Tailscale exposure |
| `Z21_PROTOCOL.md` | the Z21 LAN protocol as used here |
| `COMPUTER_VISION.md` | YOLO tracking pipeline |
| `REMOTE_VIDEO.md` | video over the network, latency |
| `SPEED_TABLE_VIEWER.md` | speed table UI, CV writes, undo |
| `SPEED_TABLE_TUNING.md`, `SPEED_TABLE_WEIGHTED_RECOMMENDATIONS.md` | how recommendations are computed |
| `SPEED_TABLE_DECODER_BEHAVIOR.md` | decoder-specific rules |
| `CV3_CV4_EDITOR.md` | acceleration and deceleration editor |
| `JMRI_INTEGRATION.md` | JMRI roster import |
| `CONSISTS.md`, `CONSIST_MAPPING.md`, `CONSIST_TRACKING.md`, `CONSIST_MANAGER_UI.md`, `VIRTUAL_CONSIST_MODE.md` | consists, mapping, tracking, editor |
| `CONSIST_ROSTER.md` | roster and configuration |
| `GPU_DEPLOYMENT.md`, `JETSON_DEPLOYMENT.md` | running the backend on other hardware |
| `CAMERA_PTZ.md`, `MOTOR_LOAD_MONITORING.md`, `LOCO_IMAGES.md` | peripherals and extras |
| `TENSORRT_OPTIMIZATION.md` | TensorRT benchmarks and setup |
| `CHROME_DEVTOOLS_OPTIMIZATION.md` | profiling the dashboard in Chrome |
| `FUTURE_IDEAS.md` | backlog, not history |
| `CHANGELOG.md` | what changed, newest first |

## Archive

`archive/` is a single flat folder: anything that describes work already done. Nothing in it is
maintained, and a broken instruction there is expected. Add a file only by moving it, with the first
line `Historical, kept as a record. Not current.`
