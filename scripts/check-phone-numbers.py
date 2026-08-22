#!/usr/bin/env python3
"""Fail if a real-looking phone number is committed.

A safety product must never ship a real person's number. But documentation and
adversarial fixtures legitimately *need* phone-shaped strings, so a blanket ban would
either be ignored or force the injection tests to be weakened.

The rule instead: phone-shaped strings are allowed only inside ranges that regulators
reserve for fiction.

  * US/NANP  555-0100 .. 555-0199   (reserved for fictional use)
  * UK       07700 900xxx           (Ofcom drama range)
  * 555-1212 style directory numbers are NOT allowed - they are real.

Usage:  check-phone-numbers.py [files...]      (default: all tracked files)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

E164 = re.compile(r"\+\d[\d\s\-().]{7,17}\d")
NANP = re.compile(r"\(?\b\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "build",
    "dist",
    ".next",
    "cdk.out",
    ".gradle",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    ".idea",
}
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".jar",
    ".apk",
    ".aab",
    ".keystore",
    ".jks",
    ".lock",
    ".woff",
    ".woff2",
    ".ttf",
}
# The wrapper jar/properties and lockfiles contain long digit runs that are not numbers.
SKIP_NAMES = {"package-lock.json", "uv.lock", "gradle-wrapper.properties"}


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def is_reserved(raw: str) -> bool:
    d = digits(raw)
    # US fictional block: NPA + 555 + 01XX, with or without country code.
    if len(d) in (10, 11):
        local = d[-10:]
        if local[3:6] == "555" and local[6:8] == "01":
            return True
    # UK Ofcom drama range: +44 7700 900xxx
    if d.startswith("447700900") or d.startswith("07700900"):
        return True
    return False


def tracked_files() -> list[Path]:
    # S607: `git` is resolved from PATH deliberately. This is a developer script
    # run inside a checkout; pinning an absolute path would break across machines.
    out = subprocess.run(
        ["git", "ls-files"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [Path(p) for p in out.splitlines() if p]


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv[1:]] or tracked_files()
    findings: list[str] = []

    for path in targets:
        if not path.is_file():
            continue
        if set(path.parts) & SKIP_DIRS or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name in SKIP_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern in (E164, NANP):
                for match in pattern.finditer(line):
                    raw = match.group(0)
                    if is_reserved(raw):
                        continue
                    if len(digits(raw)) < 10:
                        continue
                    findings.append(f"{path}:{lineno}: {raw.strip()}")

    if findings:
        print("Phone numbers that are not in a reserved fictional range:\n")
        for f in findings:
            print(f"  {f}")
        print(
            "\nUse a reserved range instead:"
            "\n  US  +1 202 555 01XX"
            "\n  UK  +44 7700 900XXX"
            "\nReal numbers must never enter this repository."
        )
        return 1

    print(f"phone numbers: clean ({len(targets)} files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
