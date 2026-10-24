import datetime as dt

import piexif
import pytest

from wow_scrn_fix import metadata

WHEN = dt.datetime(2005, 5, 27, 2, 49, 57)


@pytest.mark.parametrize("fixture", ["jpeg_bytes", "bare_jpeg_bytes"])
def test_jpeg_date_round_trips_and_keeps_image(request, fixture):
    data = request.getfixturevalue(fixture)
    new = metadata.set_date(data, "jpeg", WHEN)
    assert metadata.read_date(new, "jpeg") == WHEN
    assert metadata.image_payload(new, "jpeg") == metadata.image_payload(data, "jpeg")
    metadata.verify(data, new, "jpeg", WHEN)


def test_jpeg_keeps_jfif_first_and_other_exif_tags(jpeg_bytes):
    new = metadata.set_date(jpeg_bytes, "jpeg", WHEN)
    assert new[2:4] == b"\xff\xe0" and new[6:10] == b"JFIF"
    exif = piexif.load(new)
    assert exif["0th"][piexif.ImageIFD.Software] == b"Picasa"
    assert exif["0th"][piexif.ImageIFD.DateTime] == b"2005:05:27 02:49:57"
    assert exif["Exif"][piexif.ExifIFD.DateTimeDigitized] == b"2005:05:27 02:49:57"


def test_jpeg_redating_replaces_the_exif_segment(jpeg_bytes):
    once = metadata.set_date(jpeg_bytes, "jpeg", WHEN)
    later = dt.datetime(2026, 1, 1, 0, 0, 0)
    twice = metadata.set_date(once, "jpeg", later)
    assert twice.count(b"Exif\x00\x00") == 1
    assert metadata.read_date(twice, "jpeg") == later


def test_png_date_round_trips_and_keeps_image(png_bytes):
    new = metadata.set_date(png_bytes, "png", WHEN)
    assert metadata.read_date(new, "png") == WHEN
    assert metadata.image_payload(new, "png") == png_bytes
    assert new.index(b"eXIf") < new.index(b"IDAT")
    twice = metadata.set_date(new, "png", WHEN)
    assert twice.count(b"eXIf") == 1


def test_verify_catches_changed_image(jpeg_bytes):
    new = metadata.set_date(jpeg_bytes, "jpeg", WHEN).replace(b"\x12\x34", b"\x00\x00")
    with pytest.raises(metadata.VerifyError):
        metadata.verify(jpeg_bytes, new, "jpeg", WHEN)


def test_verify_catches_wrong_date(jpeg_bytes):
    new = metadata.set_date(jpeg_bytes, "jpeg", WHEN)
    with pytest.raises(metadata.VerifyError):
        metadata.verify(jpeg_bytes, new, "jpeg", dt.datetime(2006, 1, 1))


def test_rejects_wrong_kind(png_bytes):
    with pytest.raises(ValueError):
        metadata.set_date(png_bytes, "jpeg", WHEN)
