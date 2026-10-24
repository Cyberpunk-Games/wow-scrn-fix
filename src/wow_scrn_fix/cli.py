"""Copy screenshots into a new folder with their date taken set from the filename.

The source folder is only ever read. Without --apply nothing is written at all.
"""

import argparse
import collections
import datetime as dt
import os
from dataclasses import dataclass
from pathlib import Path

from . import metadata
from .filetimes import set_file_times
from .naming import CANONICAL_EXT, VALID_EXTS, detect_kind, parse_filename_date

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@dataclass
class Item:
    src: Path
    kind: str | None = None
    when: dt.datetime | None = None
    dest: Path | None = None
    skip: str | None = None   # why the file is deliberately left out
    error: str | None = None


def plan(src_dir, out_dir):
    """Decide, for every file in src_dir, its date and output path (or why it is skipped)."""
    items, taken = [], {}
    for src in sorted(p for p in src_dir.iterdir() if p.is_file()):
        item = Item(src)
        items.append(item)
        with open(src, "rb") as f:
            item.kind = detect_kind(f.read(16))
        if src.suffix.lower() in VIDEO_EXTS or item.kind == "mp4":
            item.skip = "video, left alone"
            continue
        if item.kind not in VALID_EXTS:
            item.skip = "not a JPEG or PNG"
            continue
        item.when = parse_filename_date(src.name)
        if item.when is None:
            item.skip = "no date in filename"
            continue
        # Fix extensions that lie about the content, e.g. JPEG data saved as .png.
        suffix = src.suffix if src.suffix.lower() in VALID_EXTS[item.kind] else CANONICAL_EXT[item.kind]
        item.dest = out_dir / (src.stem + suffix)
        key = item.dest.name.lower()
        if key in taken:
            item.error = f"output name {item.dest.name} also used by {taken[key]}"
        taken[key] = src.name
    return items


def process(item, apply):
    data = item.src.read_bytes()
    new = metadata.set_date(data, item.kind, item.when)
    metadata.verify(data, new, item.kind, item.when)
    if not apply:
        return
    # Write under a temporary name so an interrupted run never leaves a half-written file.
    tmp = item.dest.with_name(item.dest.name + ".part")
    tmp.write_bytes(new)
    metadata.verify(data, tmp.read_bytes(), item.kind, item.when)
    os.replace(tmp, item.dest)
    set_file_times(item.dest, item.when)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="wow-scrn-fix", description=__doc__.splitlines()[0])
    parser.add_argument("src", type=Path, help="folder with the original screenshots (only read, never changed)")
    parser.add_argument("--out", type=Path, help="output folder (default: <src>_fixed next to src)")
    parser.add_argument("--apply", action="store_true", help="write the output folder; without it, only report")
    parser.add_argument("-v", "--verbose", action="store_true", help="list every file, not only renames, skips and errors")
    args = parser.parse_args(argv)

    src = args.src.resolve()
    out = (args.out or src.with_name(src.name + "_fixed")).resolve()
    if not src.is_dir():
        parser.error(f"{src} is not a folder")
    if out == src:
        parser.error("--out must be a different folder; the originals are never modified")

    items = plan(src, out)
    if args.apply:
        out.mkdir(parents=True, exist_ok=True)

    counts = collections.Counter()
    for item in items:
        name = item.src.name
        if item.skip:
            print(f"skip    {name}: {item.skip}")
            counts["skipped"] += 1
            continue
        if not item.error and args.apply and item.dest.exists():
            if args.verbose:
                print(f"exists  {item.dest.name}")
            counts["already in output"] += 1
            continue
        if not item.error:
            try:
                process(item, args.apply)
            except Exception as e:  # report the file and keep going with the rest
                item.error = f"{type(e).__name__}: {e}"
        if item.error:
            print(f"ERROR   {name}: {item.error}")
            counts["errors"] += 1
            continue
        renamed = item.dest.name != name
        if renamed or args.verbose:
            arrow = f" -> {item.dest.name}" if renamed else ""
            print(f"{'rename' if renamed else 'date'}    {name}{arrow}  [{item.when:%Y-%m-%d %H:%M:%S}]")
        counts["dated"] += 1
        counts["renamed"] += renamed

    print()
    print(f"Wrote to {out}" if args.apply else f"Dry run, nothing written (output would go to {out})")
    for label in ("dated", "renamed", "already in output", "skipped", "errors"):
        print(f"  {label:18} {counts[label]}")
    return 1 if counts["errors"] else 0
