"""Constants for Rewise."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "rewise"
SCAN_INTERVAL = timedelta(seconds=30)
MIN_GAP = 1.1
BUSY_RETRY = 1.2
TIMEOUT = 10
CONF_CODE = "code"
FAN_MODES = ["auto", "low", "medium", "high"]
MIN_TEMP = 17
MAX_TEMP = 30
EXTRA_NAMES = {
    "swingV": "Swing",
    "swingH": "Horizontal swing",
    "turbo": "Turbo",
    "quiet": "Quiet",
    "econo": "Eco",
    "light": "Display light",
    "sleep": "Sleep",
    "clean": "Clean",
    "beep": "Beep",
}
