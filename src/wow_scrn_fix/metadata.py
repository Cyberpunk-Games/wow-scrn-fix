"""Write and read EXIF dates in JPEG and PNG bytes without touching the image data.

piexif is used only to parse and build the EXIF block. Splicing it into the file is
done here because piexif.insert() also deletes the JPEG's JFIF (APP0) segment.
"""

import datetime as dt
import struct
import zlib

import piexif

EXIF_FORMAT = "%Y:%m:%d %H:%M:%S"
EXIF_HEADER = b"Exif\x00\x00"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class VerifyError(Exception):
    """A rewritten file did not round-trip correctly."""


def _empty_exif():
    return {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}


def _apply_dates(exif, when):
    stamp = when.strftime(EXIF_FORMAT).encode()
    exif.setdefault("0th", {})[piexif.ImageIFD.DateTime] = stamp
    exif.setdefault("Exif", {})[piexif.ExifIFD.DateTimeOriginal] = stamp
    exif["Exif"][piexif.ExifIFD.DateTimeDigitized] = stamp


def _date_from_exif(exif):
    raw = exif.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
    if not raw:
        return None
    return dt.datetime.strptime(raw.decode().strip("\x00 "), EXIF_FORMAT)


# --- JPEG -------------------------------------------------------------------

def _jpeg_exif_span(data):
    """Return ((start, end) of the Exif APP1 segment or None, offset to insert one at)."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    pos = insert_at = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise ValueError(f"bad JPEG marker at byte {pos}")
        marker = data[pos + 1]
        if marker == 0xFF:  # fill byte
            pos += 1
            continue
        if marker in (0xDA, 0xD9):  # start of scan / end of image: headers are over
            break
        end = pos + 2 + struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if marker == 0xE1 and data[pos + 4:pos + 10] == EXIF_HEADER:
            return (pos, end), insert_at
        if marker == 0xE0:  # keep JFIF/JFXX headers first, as the spec requires
            insert_at = end
        pos = end
    return None, insert_at


def date_jpeg(data, when):
    span, insert_at = _jpeg_exif_span(data)
    exif = piexif.load(data[span[0] + 4:span[1]]) if span else _empty_exif()
    _apply_dates(exif, when)
    block = piexif.dump(exif)
    if len(block) + 2 > 0xFFFF:
        raise ValueError("EXIF block too large for a JPEG segment")
    segment = b"\xff\xe1" + struct.pack(">H", len(block) + 2) + block
    start, end = span or (insert_at, insert_at)
    return data[:start] + segment + data[end:]


# --- PNG --------------------------------------------------------------------

def _png_chunks(data):
    """Yield (type, body, raw bytes) for each chunk up to and including IEND."""
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG")
    pos = 8
    while pos + 12 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        end = pos + 12 + length
        yield kind, data[pos + 8:pos + 8 + length], data[pos:end]
        if kind == b"IEND":
            return
        pos = end
    raise ValueError("PNG has no IEND chunk")


def date_png(data, when):
    chunks = list(_png_chunks(data))
    existing = next((body for kind, body, _ in chunks if kind == b"eXIf"), None)
    exif = piexif.load(existing) if existing else _empty_exif()
    _apply_dates(exif, when)
    body = piexif.dump(exif)[len(EXIF_HEADER):]  # eXIf holds bare TIFF data
    new_chunk = struct.pack(">I", len(body)) + b"eXIf" + body + struct.pack(">I", zlib.crc32(b"eXIf" + body))
    out = [PNG_SIGNATURE]
    for kind, _, raw in chunks:
        if kind == b"eXIf":
            continue
        if kind == b"IDAT" and new_chunk:  # eXIf must come before the image data
            out.append(new_chunk)
            new_chunk = None
        out.append(raw)
    return b"".join(out)


# --- shared -----------------------------------------------------------------

def set_date(data, kind, when):
    """Return a copy of the file bytes with all EXIF date fields set to `when`."""
    return {"jpeg": date_jpeg, "png": date_png}[kind](data, when)


def read_date(data, kind):
    """Return EXIF DateTimeOriginal from file bytes, or None."""
    if kind == "jpeg":
        span, _ = _jpeg_exif_span(data)
        return _date_from_exif(piexif.load(data[span[0] + 4:span[1]])) if span else None
    body = next((body for k, body, _ in _png_chunks(data) if k == b"eXIf"), None)
    return _date_from_exif(piexif.load(body)) if body else None


def image_payload(data, kind):
    """The file bytes minus the EXIF block: must be identical before and after dating."""
    if kind == "jpeg":
        span, _ = _jpeg_exif_span(data)
        return data[:span[0]] + data[span[1]:] if span else data
    return PNG_SIGNATURE + b"".join(raw for k, _, raw in _png_chunks(data) if k != b"eXIf")


def verify(old, new, kind, when):
    if read_date(new, kind) != when:
        raise VerifyError("date did not read back correctly")
    if image_payload(new, kind) != image_payload(old, kind):
        raise VerifyError("bytes outside the EXIF block changed")
