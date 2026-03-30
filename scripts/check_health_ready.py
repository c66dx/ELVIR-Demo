#!/usr/bin/env python3
"""Chequeo externo de readiness (base de datos) vía GET /health/ready.

Exit codes:
  0 — HTTP 200, aplicación lista para recibir tráfico
  1 — HTTP 503 (BD no disponible)
  2 — error de red, timeout o respuesta inesperada

Uso:
  python scripts/check_health_ready.py --url http://localhost:8000/health/ready
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ELVIR /health/ready (database connectivity)")
    parser.add_argument("--url", default="http://localhost:8000/health/ready", help="Readiness endpoint URL")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="HTTP timeout in seconds (default: 5)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with urllib.request.urlopen(args.url, timeout=args.timeout_seconds) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 503:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
            except Exception:
                payload = {}
            print("❌ Not ready (503):", json.dumps(payload, ensure_ascii=False))
            return 1
        print(f"❌ Unexpected HTTP status: {exc.code}")
        return 2
    except Exception as exc:  # pragma: no cover - ops / network failures
        print(f"❌ Unable to fetch readiness endpoint: {exc}")
        return 2

    if status != 200:
        print(f"❌ Unexpected HTTP status: {status}")
        return 2

    print("health_ready:")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    checks = body.get("checks", {})
    if checks.get("database") == "ok":
        print("✅ Database check OK")
        return 0
    print("⚠️ Response missing checks.database=ok")
    return 2


if __name__ == "__main__":
    sys.exit(main())
