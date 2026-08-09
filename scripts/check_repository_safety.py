"""Fail CI when secrets, runtime data, or generated builds are tracked."""

from __future__ import annotations

import re
import subprocess
import sys
import argparse
from pathlib import Path
from typing import Iterable, List


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATHS = (
    re.compile(r"(^|/)(credentials|token)\.json$", re.IGNORECASE),
    re.compile(r"(^|/)client_secret[^/]*\.json$", re.IGNORECASE),
    re.compile(r"(^|/)provider_approval[^/]*\.json$", re.IGNORECASE),
    re.compile(r"(^|/)(data|logs|backups|dist)/", re.IGNORECASE),
    re.compile(r"\.(db|sqlite|sqlite3|log|pem|key)$", re.IGNORECASE),
)
SECRET_PATTERNS = (
    re.compile(r"GOCSPX-[A-Za-z0-9_-]{20,}"),
    re.compile(r'"refresh_token"\s*:\s*"(?!REDACTED|example)[^"]+"', re.IGNORECASE),
    re.compile(r'"client_secret"\s*:\s*"(?!REDACTED|example)[^"]+"', re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
TEXT_SUFFIXES = {
    ".csv", ".env", ".ini", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"
}


def tracked_files() -> List[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item]


def scan_paths(paths: Iterable[str]) -> List[str]:
    findings: List[str] = []
    for relative in paths:
        normalized = relative.replace("\\", "/")
        if any(pattern.search(normalized) for pattern in FORBIDDEN_PATHS):
            findings.append(f"forbidden tracked path: {normalized}")
            continue

        path = ROOT / relative
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        if path.stat().st_size > 2 * 1024 * 1024:
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(f"possible secret in tracked file: {normalized}")
                break
    return findings


def scan_history() -> List[str]:
    findings: List[str] = []
    objects = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    for line in objects.splitlines():
        _, _, path = line.partition(" ")
        normalized = path.replace("\\", "/")
        if normalized and any(pattern.search(normalized) for pattern in FORBIDDEN_PATHS):
            findings.append(f"forbidden path remains in Git history: {normalized}")
            if len(findings) >= 20:
                break

    patches = subprocess.run(
        ["git", "log", "-p", "--all", "--no-ext-diff", "--no-textconv"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    if any(pattern.search(patches) for pattern in SECRET_PATTERNS):
        findings.append("possible secret value remains in Git history")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true", help="scan all reachable Git history")
    args = parser.parse_args()
    findings = scan_paths(tracked_files())
    if args.history:
        findings.extend(scan_history())
    if findings:
        print("Repository safety check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    scope = "tracked files and reachable history" if args.history else "tracked files"
    print(f"Repository safety check passed for {scope}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
