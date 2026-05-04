#!/usr/bin/env python3
"""Pull every file listed in files.json from Google Drive.

Paths in files.json are relative to original_files/ (the parent of this dir).
Entries with an empty file ID are skipped.
"""
import argparse
import json
import sys
from pathlib import Path

from googleapiclient.errors import HttpError

from pull import SCRIPT_DIR, get_service, pull_file

FILES_MAP_PATH = SCRIPT_DIR / "files.json"
DEST_BASE = SCRIPT_DIR.parent  # original_files/


def load_map() -> dict:
    if not FILES_MAP_PATH.exists():
        sys.exit(f"Missing {FILES_MAP_PATH}.")
    return json.loads(FILES_MAP_PATH.read_text())


def main():
    parser = argparse.ArgumentParser(description="Pull files listed in files.json.")
    parser.add_argument(
        "names",
        nargs="*",
        help="Optional subset of names from files.json. Default: all entries.",
    )
    args = parser.parse_args()

    file_map = load_map()
    if args.names:
        unknown = [n for n in args.names if n not in file_map]
        if unknown:
            sys.exit(f"Not in files.json: {unknown}")
        file_map = {n: file_map[n] for n in args.names}

    service = get_service()
    pulled, skipped, failed = [], [], []
    for rel_path, file_id in file_map.items():
        if not file_id:
            print(f"SKIP  {rel_path}  (no file ID in files.json)")
            skipped.append(rel_path)
            continue
        dest = DEST_BASE / rel_path
        try:
            pull_file(service, file_id, dest)
            pulled.append(rel_path)
        except HttpError as e:
            print(f"FAIL  {rel_path}  ({e})")
            failed.append(rel_path)

    print()
    print(f"Pulled: {len(pulled)}   Skipped: {len(skipped)}   Failed: {len(failed)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
