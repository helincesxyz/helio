#!/usr/bin/env python3
"""Quick health check against a running Helio service.

Only talks to Helio's own local API (default http://127.0.0.1:8787) — never
to OKX directly. Useful for a fast "is everything up" check without needing
pytest or the full CLI installed; uses only the standard library.

Exit code: 0 if /status responds and every /verify row is PASS, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

STATUS_ICON = {"PASS": "✅", "FAIL": "❌", "NOT RUN": "⏳", "STALE": "⚠️"}


def _get_json(url: str, timeout: float) -> object:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    try:
        status = _get_json(f"{args.base_url}/status", args.timeout)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"❌ Could not reach Helio service at {args.base_url}: {exc}")
        print("   Is it running? Try: make serve  (or) python -m helio.cli.main serve")
        return 1

    print(f"Helio {status['version']} — mode={status['mode']} — allow_live={status['allow_live']}")
    print()

    try:
        rows = _get_json(f"{args.base_url}/verify", args.timeout)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"❌ Could not fetch /verify: {exc}")
        return 1

    all_pass = True
    for row in rows:
        icon = STATUS_ICON.get(row["status"], "?")
        print(f"{icon} {row['check']:<16} {row['status']:<8} {row['detail']}")
        if row["status"] != "PASS":
            all_pass = False

    print()
    if all_pass:
        print("All checks PASS.")
        return 0

    print(
        "Not all checks PASS. OKX-sourced rows (OKX CONNECTION, ACCOUNT, MARKET DATA,\n"
        "PORTFOLIO, SPOT EXECUTION) are only updated when Claude Code runs\n"
        "docs/runbooks/verify.md — see docs/VERIFICATION_PROTOCOL.md."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
