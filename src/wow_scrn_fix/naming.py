"""Filename date parsing and file-type detection."""

import datetime as dt
import re

# Matched against the filename without its extension.
_PATTERNS = (
    # WoW's own naming: WoWScrnShot_MMDDYY_HHMMSS (two-digit year).
    re.compile(r"WoWScrnShot_(?P<mo>\d\d)(?P<d>\d\d)(?P<y>\d\d)_(?P<h>\d\d)(?P<mi>\d\d)(?P<s>\d\d)"),
    # Capture-tool naming: "WoW YYYY-MM-DD HH-MM-SS-hh" (hh = hundredths, ignored).
    re.compile(r"WoW (?P<y>\d{4})-(?P<mo>\d\d)-(?P<d>\d\d) (?P<h>\d\d)-(?P<mi>\d\d)-(?P<s>\d\d)(?:-\d\d)?"),
)

# Extensions accepted as-is for each real file type, and the one used when renaming.
VALID_EXTS = {"jpeg": {".jpg", ".jpeg"}, "png": {".png"}}
CANONICAL_EXT = {"jpeg": ".jpg", "png": ".png"}


def parse_filename_date(name):
    """Return the naive local datetime encoded in a filename, or None."""
    stem = name.rsplit(".", 1)[0]
    for pattern in _PATTERNS:
        m = pattern.fullmatch(stem)
        if m:
            year = int(m["y"])
            if year < 100:
                year += 2000
            try:
                return dt.datetime(year, int(m["mo"]), int(m["d"]), int(m["h"]), int(m["mi"]), int(m["s"]))
            except ValueError:
                return None
    return None


def detect_kind(head):
    """Identify a file from its first bytes: 'jpeg', 'png', 'mp4' or None."""
    if head[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if head[4:8] == b"ftyp":
        return "mp4"
    return None
