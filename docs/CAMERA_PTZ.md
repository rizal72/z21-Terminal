# Camera PTZ

The C210 is nudged from the video panel: four arrows, one small step per click.
The transport is **ONVIF**, not the Tapo JSON API.

## Why ONVIF, not the Tapo API

The Tapo local JSON API (the `pytapo` library) is not usable on this firmware:
it needs the TP-Link cloud account password and, on this camera, a UDP
discovery that `pytapo` does not implement. Forcing its TPAP transport raises
`KeyError 'dev_salt'`; the legacy login refuses the camera account (`-40404`
after a few attempts, then a 30 minute suspension with `sec_left`). That path is
abandoned: do not add `pytapo` back.

ONVIF works with the **camera account** credentials already in
`config.local.json` for RTSP, over HTTP port 2020, with a WSSE UsernameToken
(PasswordDigest). No cloud password, no new account.

## Endpoints and profile

- Device service: `http://<camera>:2020/onvif/device_service`
- PTZ service: `http://<camera>:2020/onvif/service`
- Media profile: `profile_1`, discovered with `GetProfiles` as the first profile
  that carries a `PTZConfiguration` (cached; re-discovered after an error).

## Movement

`RelativeMove` is refused by this firmware (`ter:InvalidArgVal`), so one click
does two calls: `GetStatus` for the current normalized pan/tilt, then
`AbsoluteMove` at that position plus one step.

- Step: **0.01** normalized, about 5 px at 1280x720. Smaller values (0.003)
  change the reported position but are quantized away by the motor.
- Direction: right/left are `+x`/`-x`; up/down are `-y`/`+y`, because the camera
  moves its view and "up" is a negative tilt. Tilt verified on the frame; the
  pan sign follows the ONVIF convention and is confirmed the first time the
  arrows are used.
- The position is absolute, so a lost step does not accumulate.

## UI

Four buttons in a compact d-pad, bottom right of the video panel, inside the
letterbox band; hidden on mobile, where the image fills the container. They are
disabled while a request is in flight. The panel is only rendered while
expanded.

## Deploy

`requests` is the only dependency (`backend/requirements.txt`). The deploy
aliases do not run pip: install requirements on the PC before `z21-deploy-dev`
when they change.
