#!/usr/bin/env python3
"""Synchronise the single file YACL implementation into ``pymodule/yacl``.

The project ships two import styles:

* ``python/yacl.py``  -- a self contained single file you can copy anywhere.
* ``pymodule/yacl/``  -- a regular package you can put on ``PYTHONPATH``.

Both are generated from the same source: ``python/yacl.py``.  After editing
the single file, run this script::

    python pymodule/sync.py

to regenerate the package.  Use ``python pymodule/sync.py --check`` in CI to
verify that the package is up to date.
"""

from __future__ import annotations

import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent          # .../pymodule
PROJECT_ROOT = MODULE_DIR.parent                      # .../yacl
SOURCE = PROJECT_ROOT / "python" / "yacl.py"
TARGET = MODULE_DIR / "yacl"

PARSER_BEGIN = "# === BEGIN PARSER ==="
PARSER_END = "# === END PARSER ==="
DUMPER_BEGIN = "# === BEGIN DUMPER ==="
DUMPER_END = "# === END DUMPER ==="

PARSER_HEADER = '''"""Parser implementation for the YACL configuration language."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

__all__ = ["YACLDecodeError", "loads", "load"]

'''

DUMPER_HEADER = '''"""Serializer implementation for the YACL configuration language."""

from __future__ import annotations

import math
from typing import Any, Callable, Optional

__all__ = ["dumps", "dump"]

'''

INIT_CONTENT = '''"""YACL - Yet Another Config Language.

A lightweight, human readable configuration language.  This package is
generated from the single file implementation in ``python/yacl.py`` by
``sync.py``; edit that file and re-run the sync script.

The API mirrors the standard library :mod:`json` module::

    import yacl

    data = yacl.loads(text)
    text = yacl.dumps(data)
"""

from ._dumper import dump, dumps
from ._parser import YACLDecodeError, load, loads

__all__ = ["load", "loads", "dump", "dumps", "YACLDecodeError"]

__version__ = "1.0.0"
'''


def extract(text: str, begin: str, end: str, label: str) -> str:
    """Return the text between *begin* and *end*, without the markers."""
    start = text.find(begin)
    if start < 0:
        raise SystemExit(f"error: marker {begin!r} not found in {SOURCE}")
    start += len(begin)
    stop = text.find(end, start)
    if stop < 0:
        raise SystemExit(f"error: marker {end!r} not found in {SOURCE}")
    section = text[start:stop].strip("\n")
    if not section.strip():
        raise SystemExit(f"error: section {label!r} is empty")
    return section


def render() -> dict[str, str]:
    """Build the package file contents from the single file source."""
    text = SOURCE.read_text(encoding="utf-8")
    parser = extract(text, PARSER_BEGIN, PARSER_END, "parser")
    dumper = extract(text, DUMPER_BEGIN, DUMPER_END, "dumper")
    return {
        "_parser.py": PARSER_HEADER + parser + "\n",
        "_dumper.py": DUMPER_HEADER + dumper + "\n",
        "__init__.py": INIT_CONTENT,
    }


def main(argv: list[str]) -> int:
    check = "--check" in argv
    if not SOURCE.is_file():
        raise SystemExit(f"error: source not found: {SOURCE}")

    files = render()
    changed: list[str] = []

    for name, content in files.items():
        path = TARGET / name
        try:
            current = path.read_text(encoding="utf-8") if path.is_file() else None
        except OSError:
            current = None

        if check:
            if current != content:
                changed.append(name)
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        if current != content:
            path.write_text(content, encoding="utf-8")
            changed.append(name)

    if check:
        if changed:
            print("out of date: " + ", ".join(changed))
            return 1
        print("pymodule is up to date")
        return 0

    if changed:
        print("synced: " + ", ".join(changed))
    else:
        print("pymodule already up to date")
    print(f"source: {SOURCE}")
    print(f"target: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))