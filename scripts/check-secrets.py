#!/usr/bin/env python3
"""Fail if something that looks like a credential is committed.

Deliberately simple and high-signal. This is a last line of defence, not a replacement
for keeping secrets in Secrets Manager.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{36,}\b")),
    (
        "bearer secret assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*"
            r"[\"'][A-Za-z0-9/+=_\-]{20,}[\"']"
        ),
    ),
]

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
    ".woff",
    ".woff2",
    ".ttf",
}
SKIP_NAMES = {"package-lock.json", "uv.lock", "check-secrets.py"}


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
        # An .env must never be tracked at all.
        if path.name == ".env" or path.name.startswith(".env."):
            if path.name != ".env.example":
                findings.append(f"{path}: environment file must not be committed")
                continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(f"{path}:{lineno}: {label}")

    if findings:
        print("Possible secrets detected:\n")
        for f in findings:
            print(f"  {f}")
        print("\nSecrets belong in AWS Secrets Manager. See docs/SECURITY.md.")
        return 1

    print(f"secrets: clean ({len(targets)} files checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
