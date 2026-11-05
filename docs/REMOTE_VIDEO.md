# Remote video: latency and plan

**Status**: phase 1 implemented (latest-frame hub), not yet deployed. Phase 2
planned. Measurements 2026-11-05, from an office network over Tailscale, backend
on the gaming PC, frontend in Chrome.

## The problem

A loco light toggled in the UI appeared in the video about 30 s later.

| Measurement | Panel open | Panel closed |
| --- | --- | --- |
| `tailscale ping` | 1.14 s | 0.46 s |
| `/api/status` | 2.0-2.3 s | 1.7 s |
| MJPEG stream | 0.40 fps, 594 kbit/s | 1.70 fps, 2.7 Mbit/s |
| Frame | 195 KB, 1280x720 | same |

The path carried ~2.7 Mbit/s. The feed offered 30 fps x 195 KB, about 47 Mbit/s,
and never dropped a frame. The generator read the RTSP stream in lockstep with
the HTTP response: when the client was slower, the `yield` blocked, the RTSP
buffer filled, and the stream fell behind at about 0.94 s per second. Thirty
seconds of lag after half a minute.

The stream also saturated the home uplink: the RTT halved when the panel was
closed, so the bufferbloat slowed the control WebSocket too.

## Architecture

- **Tracking daemon**: its own `cv2.VideoCapture`, `fps.active = 30`
  (`fps.idle = 1`), GPU inference. This is the recognition path and stays at
  full rate; nothing here touches it.
- **Video feed** (`backend/video_feed.py`, phase 1): one shared `VideoCapture`
  for every viewer, a reader thread keeping only the newest frame, viewer
  refcount. Each viewer gets its own generator, overlay drawing and JPEG encode,
  so its rate adapts independently.
- The "Frame Queue Sharing" described in `COMPUTER_VISION.md` is no longer in
  the code and must not come back: a queue between the two pipelines couples
  their rates, so a slow viewer could stall recognition.

RTSP connections: 2 (tracking + feed), whatever the number of viewers. Before
phase 1 it was 2 + (viewers - 1).

## Phase 1: latest frame, automatic rate

- `_LatestFrame` in `video_feed.py`: one `VideoCapture`, a daemon reader thread
  doing `read()` continuously, latest frame under a lock, opened by the first
  viewer and closed by the last (the reader notices the stop between two reads;
  a hung read can delay the close beyond the RTSP timeout the capture asks for);
  reconnect with a 2 s backoff.
- `generate_video_frames`: copies the latest frame, draws gates/delta-t/debug
  boxes, encodes JPEG at quality 65, yields; sleeps only when the send took
  less than `1/fps.video_feed`. That value is a **ceiling**, not a target, so
  the stream adapts by itself: high on the LAN, low remotely, always live.
- No resize: the gate editor maps clicks against the image's native size
  (1280x720). A scaled stream would break stored gate coordinates.
- No manual switch when leaving or entering the house: nothing to configure.

Measured on the implementer's Mac (camera reached over Tailscale, 2.1 fps
available): 101 KB per frame at quality 65, against 195 KB at 80. At the
measured 2.7 Mbit/s that is about 3 fps live, up from 0.4 fps with a growing
lag. On the LAN the ceiling of 30 applies.

Acceptance tests, still to run from outside the house after deployment:

1. Panel open: fps and bitrate, and the RTT must stay close to the closed value
   (0.46 s). If it climbs back to ~1 s the uplink is still saturated.
2. End to end: send F0, timestamp the frames, measure when the brightness
   changes. Target below 2 s.
3. The tracking log still shows 30 fps active / 1 idle; gates and delta-t work;
   the debug boxes are aligned with the image.
4. Two viewers (Mac and phone): both live, neither slowing the other.

Deploy: backend only, `git pull` + `z21-restart` on the PC, no frontend rebuild.

## Phase 2: WebRTC passthrough

Phase 1 fixes the lag, but the remote frame rate stays bounded by the JPEG size
over the uplink: about 3 fps at 720p. Real remote video needs the camera's
H.264, not a re-encoded JPEG.

Surveyed 2026-11-05; versions and facts from the projects' own docs:

- **MediaMTX 1.21.3** (25 Oct 2026): single `mediamtx.exe`, WebRTC/WHEP,
  LL-HLS, RTSP; ships `reader.js` to embed a WHEP stream in our own page;
  internal users / HTTP / JWT auth; Windows service via WinSW.
- **go2rtc 1.9.15** (25 Oct 2026): single Windows binary, RTSP->WebRTC/MSE/HLS,
  better codec auto-negotiation, but no built-in auth and no Windows service
  recipe.
- **Audio is free**: the camera's PCM A-law (G.711) passes through WebRTC
  untouched in both (MediaMTX lists G711 PCMA/PCMU; go2rtc accepts PCMA and
  only resamples when the rate differs). No transcode, no FFmpeg.
- **Network**: `tailscale serve` proxies HTTP to localhost and forwards TCP only,
  so it cannot carry the WebRTC UDP port (8189 in MediaMTX). Connect to the
  Tailscale IP directly: no proxy, no STUN/TURN. Open the Windows firewall for
  UDP 8189 and set `webrtcAdditionalHosts` to the tailnet address if the ICE
  candidate picks the LAN IP.
- **Browsers**: WebRTC on Chrome, Firefox, Safari 14+ (iPhone Safari 17.1+);
  MSE not on iPhone, so keep LL-HLS as the iOS fallback. Serve page and WHEP
  over the same scheme (HTTPS page, HTTPS WHEP).
- **Not worth it now**: WebTransport became Baseline in March 2026 and WebCodecs
  in Safari 26.0, but no off-the-shelf camera product uses them; MoQ is still a
  draft. Revisit when an embeddable player exists.
- **The real cost**: gates, delta-t panel and debug boxes are drawn by the
  backend into the JPEG today. With H.264 they must be drawn client-side:
  `<video>` plus an `<svg viewBox="0 0 1280 720">` absolutely positioned over
  it, sized from `video.videoWidth/videoHeight` once metadata is available, and
  a canvas redrawn in `requestVideoFrameCallback` for the boxes. That is the
  bulk of the work, not the transport.

Steps, when the PC is back home:

1. Install MediaMTX (or go2rtc) on the PC, point it at `stream2`, credentials in
   `config.local.json`.
2. Open UDP 8189 (or go2rtc's 8555) in the Windows firewall and connect over
   the tailnet IP; verify WebRTC and audio from outside.
3. Prototype the client-side overlay: gates, delta-t text, debug boxes, using
   the tracking data already arriving on the WebSocket.
4. Keep the MJPEG endpoint as a fallback; the gate editor keeps using it.
5. Rebuild and deploy the frontend, then update this page and the changelog.

## Hosting modes

Three modes, not one. The code is the same; what changes is which machine holds
the camera and the Z21 on its own LAN.

- **Remote, primary: the PC at home.** Fixed, always on, GPU with TensorRT,
  camera and Z21 on its LAN. Backend, sidecar and database live here. This is
  the host for demos and for watching from outside, and the one the phase 2
  sidecar is installed on first.
- **At home: the Mac.** Tests and demos for friends without powering the PC at
  all. The Mac is on the home LAN, so camera and Z21 are local. Same code, same
  sidecar if wanted. Events are written to the Mac's database: switching back to
  the PC means copying the database (see AGENTS.md) or accepting the
  divergence. Never run both backends at once on the same layout.
- **Future, to evaluate: the Mac left on at home as a server,** watched from a
  phone while away. Technically the same as the second mode, since the Mac is on
  the home LAN, but it needs the backend and the sidecar as launchd agents rather
  than a tmux session, the Mac kept awake with the lid closed (energy settings or
  `caffeinate`), and Tailscale up. Database divergence applies as above. Decide
  later, on power draw and reliability.

In every mode the host is the machine with the camera on its own LAN. A machine
reaching the camera over Tailscale can stream but not do recognition well: the
Mac in the office measured 2.1 fps from the camera against the LAN's 30.

## Not doing

- Merging the viewer capture with the tracking capture.
- Resizing the MJPEG stream while the gate editor depends on native coordinates.
- Lowering `fps.active` to save bandwidth: recognition stays at full rate.
