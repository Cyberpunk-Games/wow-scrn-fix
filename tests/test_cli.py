import datetime as dt
import os

import pytest

from wow_scrn_fix import metadata
from wow_scrn_fix.cli import main


@pytest.fixture
def src(tmp_path, jpeg_bytes, png_bytes):
    d = tmp_path / "WoW"
    d.mkdir()
    (d / "WoWScrnShot_052705_024957.jpg").write_bytes(jpeg_bytes)
    (d / "WoWScrnShot_042826_220257.png").write_bytes(jpeg_bytes)  # JPEG data with a .png name
    (d / "WoWScrnShot_010118_012245.jpeg").write_bytes(jpeg_bytes)
    (d / "WoW 2010-01-05 20-09-56-05.png").write_bytes(png_bytes)
    (d / "World Of Warcraft 2024.07.29 - 10.56.06.01.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
    (d / "wowremix-xpto70.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom")
    return d


def snapshot(folder):
    return {p.name: (p.read_bytes(), p.stat().st_mtime) for p in folder.iterdir()}


def test_dry_run_writes_nothing(src, tmp_path):
    before = snapshot(src)
    assert main([str(src)]) == 0
    assert not (tmp_path / "WoW_fixed").exists()
    assert snapshot(src) == before


def test_apply_writes_dated_copies_and_leaves_source_alone(src, tmp_path):
    before = snapshot(src)
    assert main([str(src), "--apply"]) == 0
    out = tmp_path / "WoW_fixed"
    assert sorted(p.name for p in out.iterdir()) == [
        "WoW 2010-01-05 20-09-56-05.png",
        "WoWScrnShot_010118_012245.jpg",  # .jpeg normalised to .jpg
        "WoWScrnShot_042826_220257.jpg",  # extension fixed to match content
        "WoWScrnShot_052705_024957.jpg",
    ]
    fixed = out / "WoWScrnShot_052705_024957.jpg"
    when = dt.datetime(2005, 5, 27, 2, 49, 57)
    assert metadata.read_date(fixed.read_bytes(), "jpeg") == when
    assert os.stat(fixed).st_mtime == pytest.approx(when.timestamp())
    assert snapshot(src) == before


def test_rerun_skips_files_already_in_output(src, tmp_path, capsys):
    main([str(src), "--apply"])
    capsys.readouterr()
    assert main([str(src), "--apply"]) == 0
    assert "already in output  4" in capsys.readouterr().out


def test_jpg_and_jpeg_with_same_stem_is_an_error(src, jpeg_bytes, capsys):
    (src / "WoWScrnShot_010118_012245.jpg").write_bytes(jpeg_bytes)
    assert main([str(src)]) == 1
    assert "also used by" in capsys.readouterr().out


def test_refuses_to_write_into_source(src):
    with pytest.raises(SystemExit):
        main([str(src), "--out", str(src), "--apply"])
