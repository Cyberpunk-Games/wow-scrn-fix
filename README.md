# wow-scrn-fix

Sets the "date taken" of World of Warcraft screenshots from their filenames, so photo
apps and Explorer sort them in the order they were actually taken.

The screenshots lost their original dates along the way (every file showed the date
it was copied, and none had an EXIF date). The date in the filename is the source of
truth.

## What it does

For every screenshot in the source folder it writes a copy to a separate output folder
(default `<source>_fixed`) with:

- **EXIF dates**: `DateTimeOriginal`, `DateTimeDigitized` and `DateTime`. Inside the file
  itself, so they survive copying and uploading. JPEGs get an EXIF segment and PNGs an
  `eXIf` chunk.
- **Windows file dates**: created, modified and accessed. These help Explorer, but any
  later copy or download resets them.
- **A consistent extension** that follows the content: all JPEGs become `.jpg` (including
  `.jpeg` files and JPEG data named `.png`), PNGs stay `.png`.

Safety:

- The source folder is **only read**, never modified.
- Without `--apply` it is a dry run: it reports what would happen and writes nothing.
- Only the EXIF block changes. Every other byte, including the image data and the JFIF
  header, stays identical. Each file is checked after writing: the date must read back
  and all bytes outside the EXIF block must match the original.
- Files are written under a `.part` name and renamed only when complete. Rerunning
  skips files already in the output folder, so an interrupted run can just be restarted.

Left out on purpose:

- **Videos** (`.mp4` etc.): left alone. Their embedded dates were already correct.
- Files with no date in the name, e.g. `wowremix-xpto70.mp4`.

## Filename patterns

| Pattern | Example | Note |
|---|---|---|
| `WoWScrnShot_MMDDYY_HHMMSS` | `WoWScrnShot_052705_024957.jpg` = 2005-05-27 02:49:57 | WoW's own naming; two-digit year → 20YY |
| `WoW YYYY-MM-DD HH-MM-SS-hh` | `WoW 2010-01-05 20-09-56-05.png` | hundredths ignored |

Filename times are local time (Greece). EXIF dates have no time zone and are written
as-is. Windows file dates are converted using the time zone of the computer running
the tool.

## Setup

Requires Python 3.10+.

```
py -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
```

## Usage

```
.venv\Scripts\wow-scrn-fix WoW              # dry run: report only
.venv\Scripts\wow-scrn-fix WoW -v           # dry run, list every file
.venv\Scripts\wow-scrn-fix WoW --apply      # write WoW_fixed\
.venv\Scripts\wow-scrn-fix WoW --out D:\Pics --apply
```

Close Explorer and photo-viewer windows on the folder while it runs. They can briefly
lock files for thumbnails, which makes a write fail. Failed files are reported, and a
rerun picks them up.

## Tests

```
.venv\Scripts\python -m pytest
.venv\Scripts\python -m pytest tests/test_metadata.py::test_png_date_round_trips_and_keeps_image
```
