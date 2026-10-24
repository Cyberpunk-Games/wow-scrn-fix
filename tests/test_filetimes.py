import datetime as dt
import os
import sys

import pytest

from wow_scrn_fix.filetimes import set_file_times


def test_sets_modified_time(tmp_path):
    f = tmp_path / "x.jpg"
    f.write_bytes(b"x")
    when = dt.datetime(2005, 5, 27, 2, 49, 57)
    set_file_times(f, when)
    assert os.stat(f).st_mtime == pytest.approx(when.timestamp())


@pytest.mark.skipif(sys.platform != "win32", reason="creation time is Windows-only")
def test_sets_creation_time_on_windows(tmp_path):
    f = tmp_path / "x.jpg"
    f.write_bytes(b"x")
    when = dt.datetime(2010, 1, 5, 20, 9, 56)
    set_file_times(f, when)
    assert os.stat(f).st_birthtime == pytest.approx(when.timestamp())
