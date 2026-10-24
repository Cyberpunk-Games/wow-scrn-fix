import struct
import zlib

import piexif
import pytest


def _png_chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


@pytest.fixture
def jpeg_bytes():
    """Minimal JPEG laid out like the real screenshots: JFIF APP0, then Exif APP1 (Software=Picasa)."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    exif = piexif.dump({"0th": {piexif.ImageIFD.Software: b"Picasa"}})
    app1 = b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif
    sos = b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00"
    return b"\xff\xd8" + app0 + app1 + sos + b"\x12\x34\x56\x78" + b"\xff\xd9"


@pytest.fixture
def bare_jpeg_bytes(jpeg_bytes):
    """Same JPEG without any EXIF segment."""
    start = jpeg_bytes.index(b"\xff\xe1")
    end = start + 2 + struct.unpack(">H", jpeg_bytes[start + 2:start + 4])[0]
    return jpeg_bytes[:start] + jpeg_bytes[end:]


@pytest.fixture
def png_bytes():
    """1x1 grayscale PNG with no metadata."""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(b"\x00\x80"))
        + _png_chunk(b"IEND", b"")
    )
