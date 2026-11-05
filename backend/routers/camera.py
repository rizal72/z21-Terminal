"""
Camera PTZ control over ONVIF.

The camera exposes the standard ONVIF PTZ service on port 2020 and accepts the
camera account credentials that RTSP already uses, so no cloud login is
involved. This firmware refuses RelativeMove (InvalidArgVal), so a click reads
the current normalized position and writes it back moved by one small step with
AbsoluteMove.

Tapo's local JSON API is not used: it requires the TP-Link cloud password and,
on this firmware, a UDP discovery that the Python library does not implement.
"""
import asyncio
import base64
import datetime
import hashlib
import os
import re
import threading
from typing import Dict, Tuple
from xml.sax.saxutils import escape

from fastapi import APIRouter

from config_loader import load_config
from log_colors import log

router = APIRouter()

# Normalized pan/tilt step: the camera quantizes small values away, 0.01 moves
# the image by roughly 5 px at 1280x720.
STEP = 0.01
_PAN_TILT_SPACE = "http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace"
_SERVICE_PATH = "/onvif/service"

# Offsets per direction. The camera moves its view, so "up" is a negative tilt.
_STEPS = {
    "left": (-STEP, 0.0),
    "right": (STEP, 0.0),
    "up": (0.0, -STEP),
    "down": (0.0, STEP),
}

_profile_token = None
_move_lock = threading.Lock()


def _camera_config() -> Tuple[str, str, str]:
    camera = load_config().get("camera", {})
    host = camera.get("ip")
    user = camera.get("username")
    password = camera.get("password")
    if not host or not user or not password:
        raise RuntimeError("Camera credentials missing in config.local.json")
    return host, user, password


def _wsse(username: str, password: str) -> str:
    nonce = os.urandom(16)
    created = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    digest = base64.b64encode(
        hashlib.sha1(nonce + created.encode() + password.encode()).digest()
    ).decode()
    return (
        '<soap:Header><Security xmlns="http://docs.oasis-open.org/wss/2004/01/'
        'oasis-200401-wss-wssecurity-secext-1.0.xsd"><UsernameToken>'
        f"<Username>{escape(username)}</Username>"
        '<Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-'
        f'username-token-profile-1.0#PasswordDigest">{digest}</Password>'
        '<Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-'
        f'wss-soap-message-security-1.0#Base64Binary">{base64.b64encode(nonce).decode()}</Nonce>'
        f"<Created>{created}</Created>"
        "</UsernameToken></Security></soap:Header>"
    )


def _call(host: str, user: str, password: str, body: str) -> str:
    # Local import: the backend must start even before pip installs requests.
    import requests

    envelope = (
        '<?xml version="1.0"?>'
        '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
        f"{_wsse(user, password)}<soap:Body>{body}</soap:Body></soap:Envelope>"
    )
    response = requests.post(
        f"http://{host}:2020{_SERVICE_PATH}",
        data=envelope,
        headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        timeout=8,
    )
    response.raise_for_status()
    return response.text


def _get_profile_token(host: str, user: str, password: str) -> str:
    """First media profile that carries a PTZ configuration, cached."""
    global _profile_token
    if _profile_token is None:
        text = _call(
            host, user, password,
            '<GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>',
        )
        blocks = re.findall(
            r'<(?:[\w]+:)?Profiles[^>]*token="([^"]+)"(.*?)</(?:[\w]+:)?Profiles>',
            text, re.S,
        )
        for token, block in blocks:
            if "PTZConfiguration" in block:
                _profile_token = token
                break
        else:
            if not blocks:
                raise RuntimeError("No ONVIF profile returned")
            _profile_token = blocks[0][0]
    return _profile_token


def _position(host: str, user: str, password: str, profile: str) -> Tuple[float, float]:
    text = _call(
        host, user, password,
        f'<GetStatus xmlns="http://www.onvif.org/ver20/ptz/wsdl">'
        f"<ProfileToken>{profile}</ProfileToken></GetStatus>",
    )
    tag = re.search(r'<(?:\w+:)?PanTilt\b[^>]*>', text)
    if not tag:
        raise RuntimeError("PTZ position missing in GetStatus reply")
    x = re.search(r'\bx="([^"]+)"', tag.group(0))
    y = re.search(r'\by="([^"]+)"', tag.group(0))
    if not (x and y):
        raise RuntimeError("PTZ position missing in GetStatus reply")
    return float(x.group(1)), float(y.group(1))


def _move_to(host: str, user: str, password: str, profile: str, x: float, y: float) -> None:
    _call(
        host, user, password,
        f'<AbsoluteMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">'
        f"<ProfileToken>{profile}</ProfileToken><Position>"
        f'<PanTilt xmlns="http://www.onvif.org/ver10/schema" Space="{_PAN_TILT_SPACE}" '
        f'x="{x:.6f}" y="{y:.6f}"/></Position></AbsoluteMove>',
    )


@router.post("/api/camera/step")
async def camera_step(payload: Dict[str, str]):
    """Move the camera by one step: left, right, up or down."""
    direction = (payload.get("direction") or "").strip().lower()
    if direction not in _STEPS:
        return {"success": False, "error": "direction must be left, right, up or down"}

    dx, dy = _STEPS[direction]

    def move():
        with _move_lock:  # serialize clicks so two tabs cannot lose a step
            host, user, password = _camera_config()
            profile = _get_profile_token(host, user, password)
            x, y = _position(host, user, password, profile)
            x = min(1.0, max(-1.0, x + dx))
            y = min(1.0, max(-1.0, y + dy))
            _move_to(host, user, password, profile, x, y)

    global _profile_token
    try:
        await asyncio.to_thread(move)
        return {"success": True}
    except Exception as e:
        # Re-discover the profile next time: a camera reboot may change it.
        _profile_token = None
        log('[CAMERA]', f"PTZ step {direction} failed: {e}")
        return {"success": False, "error": str(e)}
