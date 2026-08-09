"""Fetch NLVE's private API into an atomic HAI Generic JSON Feed file."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests


def _validate_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    if parsed.scheme == "https" and parsed.hostname:
        return raw_url.rstrip("/")
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return raw_url.rstrip("/")
    raise ValueError("NLVE_API_URL must use HTTPS unless it points to loopback")


def _validate_feed(payload: object) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("NLVE returned an invalid HAI feed envelope")
    if len(payload["items"]) > 500:
        raise ValueError("NLVE returned more than 500 HAI feed items")
    for index, item in enumerate(payload["items"]):
        if not isinstance(item, dict):
            raise ValueError(f"HAI feed item {index} is not an object")
        for required in ("externalId", "provider", "itemType"):
            if not str(item.get(required) or "").strip():
                raise ValueError(f"HAI feed item {index} is missing {required}")
        if item.get("provider") != "generic_json_feed":
            raise ValueError(f"HAI feed item {index} has an unsupported provider")
    return payload


def sync_feed(api_url: str, token: str, output_path: str, limit: int = 100) -> dict:
    """Fetch one bounded feed and replace the destination only after validation."""
    base_url = _validate_url(api_url)
    token = token.strip()
    if len(token) < 32:
        raise ValueError("NLVE_API_TOKEN must contain at least 32 characters")
    if not 1 <= int(limit) <= 500:
        raise ValueError("limit must be between 1 and 500")

    response = requests.get(
        f"{base_url}/api/v1/hai/feed",
        params={"limit": int(limit)},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=(5, 15),
        allow_redirects=False,
    )
    if response.status_code != 200:
        raise RuntimeError(f"NLVE HAI feed request failed with HTTP {response.status_code}")
    if len(response.content) > 5 * 1024 * 1024:
        raise RuntimeError("NLVE HAI feed exceeds 5 MiB")
    feed = _validate_feed(response.json())

    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(feed, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return {"path": str(destination), "items": len(feed["items"]), "cursor": feed.get("cursor", "")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sync the NLVE read-only HAI feed")
    parser.add_argument("output", help="HAI feed JSON destination")
    parser.add_argument("--url", default=os.environ.get("NLVE_API_URL", "http://127.0.0.1:8765"))
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    result = sync_feed(args.url, os.environ.get("NLVE_API_TOKEN", ""), args.output, args.limit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
