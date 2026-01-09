"""
ANSI color codes for log output prefixes and status keywords.
Compatible with dark and light terminal backgrounds.
Centralized mapping for easy maintenance.
"""

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
