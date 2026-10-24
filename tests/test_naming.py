import datetime as dt

import pytest

from wow_scrn_fix.naming import detect_kind, parse_filename_date


@pytest.mark.parametrize("name, expected", [
    ("WoWScrnShot_052705_024957.jpg", dt.datetime(2005, 5, 27, 2, 49, 57)),
    ("WoWScrnShot_123125_224416.jpg", dt.datetime(2025, 12, 31, 22, 44, 16)),
    ("WoWScrnShot_010118_012245.jpeg", dt.datetime(2018, 1, 1, 1, 22, 45)),
    ("WoWScrnShot_102126_090938.png", dt.datetime(2026, 10, 21, 9, 9, 38)),
    ("WoW 2010-01-05 20-09-56-05.png", dt.datetime(2010, 1, 5, 20, 9, 56)),
])
def test_parses_known_patterns(name, expected):
    assert parse_filename_date(name) == expected


@pytest.mark.parametrize("name", [
    "wowremix-xpto70.mp4",
    "WoWScrnShot_132705_024957.jpg",       # month 13
    "WoWScrnShot_023005_024957.jpg",       # 30 February
    "WoWScrnShot_052705_024957(1).jpg",    # copy suffix: not an exact match
    "World Of Warcraft 2024.07.29 - 10.56.06.01.mp4",
])
def test_rejects_other_names(name):
    assert parse_filename_date(name) is None


def test_detect_kind():
    assert detect_kind(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "jpeg"
    assert detect_kind(b"\x89PNG\r\n\x1a\n\x00\x00") == "png"
    assert detect_kind(b"\x00\x00\x00\x18ftypisom") == "mp4"
    assert detect_kind(b"GIF89a") is None
