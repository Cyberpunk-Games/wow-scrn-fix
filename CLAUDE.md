# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Python CLI (`wow-scrn-fix`) that copies WoW screenshots from `WoW/` to `WoW_fixed/`,
writing the date encoded in each filename into EXIF and the Windows file times.
User-facing behaviour and filename patterns are in README.md.

## Commands

```
py -m venv .venv && .venv\Scripts\python -m pip install -e .[dev]   # setup
.venv\Scripts\python -m pytest                                        # all tests
.venv\Scripts\python -m pytest tests/test_metadata.py::test_png_date_round_trips_and_keeps_image
.venv\Scripts\wow-scrn-fix WoW                                        # dry run on real data (read-only)
```

## Architecture (`src/wow_scrn_fix/`)

- `naming.py`: filename to naive local datetime; file type sniffed from magic bytes
  (extensions are not trusted).
- `metadata.py`: pure functions on `bytes`: `set_date`, `read_date`, `image_payload`, `verify`.
- `filetimes.py`: `os.utime` plus Windows creation time via ctypes `SetFileTime`.
- `cli.py`: `plan()` picks each file's date, output name or skip reason. `process()`
  builds new bytes, verifies, writes `<name>.part`, re-verifies from disk, `os.replace`s,
  then sets file times. The dry run does the same in-memory verify without writing.

## Invariants

- **Never write to the source folder.** `cli.main` rejects `--out == src`.
- **Only the EXIF block may change.** `verify()` requires `image_payload(old) == image_payload(new)`.
  Never use `piexif.insert()`: it silently deletes the JPEG's JFIF APP0 segment. piexif
  is only for `load`/`dump`; segment splicing lives in `metadata.py`.
- **Filenames are the source of truth for dates** (local Greek time). No image had an
  embedded date; the videos' embedded dates matched their filenames.
- **Videos are excluded on purpose** (user's decision): their embedded dates are already correct.

## Data facts (`WoW/`, ~1.3 GB, git-ignored)

- 2,390 files: 2,179 `.jpg`, 32 `.jpeg`, 169 `.png`, 10 `.mp4`. All JPEGs have EXIF
  `Software=Picasa` and no dates.
- 95 `.png` files are really JPEG data (all 2026); their copies get renamed to `.jpg`.
- `WoWScrnShot_MMDDYY_HHMMSS` uses a two-digit year (2005 to 2026 present).
- `wowremix-xpto70.mp4` has no date anywhere.

## Working rules

- **Never use em-dash (U+2014)** anywhere: code strings, messages, commit messages, PR
  descriptions, docs, replies. Use hyphen, comma, colon or parentheses. When editing a line
  that already has one, replace it; no blanket sweeps.
- Stick to the exact scope of the request and ask before expanding it. Don't change which
  files are processed, the output naming, or which EXIF fields are written unless asked.
- If a fix approach fails after 2 attempts, stop and discuss alternatives instead of iterating.
- After editing text with special characters (Unicode, byte literals), diff-check the result.

## Shortcuts

- `mc`: draft a commit message for changes since the last commit and print it in a fenced
  block. Do NOT run `git commit`. Use `git status` + `git diff HEAD`; check
  `git log --oneline -10` for style. No em-dash, no `Co-Authored-By` trailer.
- `mcc`: like `mc`, but commit, split by feature.
- `ch`: list the notable changes since the last CHANGELOG entry.
