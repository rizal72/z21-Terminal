"""
ANSI color codes for log output prefixes and status keywords.
Compatible with dark and light terminal backgrounds.
Centralized mapping for easy maintenance.
"""

import sys

# Mapping PREFIX → COLOR (single source of truth)
PREFIXES = {
    '[INIT]': '\033[97m',    # White bright - startup (importante, alta visibilità)
    '[SHUT]': '\033[35m',    # Viola/Magenta normale - shutdown
    '[ERROR]': '\033[91m',   # Red bright - errori critici
    '[WARN]': '\033[93m',    # Yellow bright - warnings
    '[OK]': '\033[92m',      # Green bright - success messages
    '[FAIL]': '\033[91m',    # Red bright - failure messages
    '[STOP]': '\033[91m',    # Red bright - emergency/stop commands
    '[CV]': '\033[91m',      # Red bright - operazioni CV critiche
    '[COMP]': '\033[95m',    # Magenta bright - auto-compensation
    '[VIRT]': '\033[36m',    # Cyan normale - virtual mode (frequente, tecnico)
    '[SYNC]': '\033[92m',    # Green bright - sync operations
    '[DETECT]': '\033[96m',  # Cyan bright - YOLO detection/tracking
    '[GATE]': '\033[94m',    # Blue bright - gate crossings
    '[WS]': '\033[34m',      # Blue normale - websocket connections
    '[OVFL]': '\033[95m',    # Magenta bright - overflow
    '[SPEED]': '\033[38;5;208m',  # Orange - speed setting events
    '[ANALYTICS]': '\033[38;5;213m',  # Pink - analytics/metrics
    '[SESSION]': '\033[38;5;213m',  # Pink - session lifecycle (same as ANALYTICS)
    '[SETTINGS]': '\033[38;5;220m',  # Gold/yellow - configuration changes
}

RESET = '\033[0m'

# Status keyword colors (unchanged)
STATUS_GREEN = '\033[92m'   # SYNCED
STATUS_YELLOW = '\033[93m'  # WARNING
STATUS_RED = '\033[91m'     # CRITICAL


def log(prefix, message):
    """
    Centralized logging with colored prefix.

    Args:
        prefix: One of the keys in PREFIXES dict (e.g., '[ERROR]', '[INIT]')
        message: Log message text

    Example:
        log('[ERROR]', 'File not found')
        log('[INIT]', 'Backend starting...')
    """
    color = PREFIXES.get(prefix, '')
    print(f"{color}{prefix}{RESET} {message}")


def colorize_status(text: str) -> str:
    """
    Colorize status keywords in text (SYNCED, WARNING, CRITICAL).

    Args:
        text: Input text containing status keywords

    Returns:
        Text with colored status keywords
    """
    text = text.replace('SYNCED', f'{STATUS_GREEN}SYNCED{RESET}')
    text = text.replace('WARNING', f'{STATUS_YELLOW}WARNING{RESET}')
    text = text.replace('CRITICAL', f'{STATUS_RED}CRITICAL{RESET}')
    return text


class ColoredOutput:
    """
    Wrapper for sys.stdout that automatically adds colored prefixes to error/warning messages.
    Intercepts all print() calls and prepends [ERROR] or [WARN] prefix if needed.
    """
    def __init__(self, stream):
        self.stream = stream
        self.error_prefix = '\033[91m[ERROR]\033[0m'    # Red bright [ERROR] prefix
        self.warn_prefix = '\033[93m[WARN]\033[0m'      # Yellow bright [WARN] prefix

    def write(self, text):
        """Intercept write() and add prefix if contains error/warning keywords"""
        if text and text.strip():
            text_lower = text.lower()

            # Check if already has a colored prefix (e.g., [INIT], [WS], etc.)
            has_prefix = any(prefix in text for prefix in PREFIXES.keys())

            # Add [ERROR] prefix if contains "error" and doesn't have a prefix already
            if 'error' in text_lower and not has_prefix:
                text = f"{self.error_prefix} {text}"
            # Add [WARN] prefix if contains "warning" and doesn't have a prefix already
            elif 'warning' in text_lower and not has_prefix:
                text = f"{self.warn_prefix} {text}"

        self.stream.write(text)

    def flush(self):
        """Forward flush to underlying stream"""
        self.stream.flush()

    def __getattr__(self, name):
        """Forward all other attributes to underlying stream"""
        return getattr(self.stream, name)


def enable_auto_coloring():
    """
    Enable automatic coloring of error/warning messages in all print() output.
    Call this once at application startup.
    """
    if not isinstance(sys.stdout, ColoredOutput):
        sys.stdout = ColoredOutput(sys.stdout)
