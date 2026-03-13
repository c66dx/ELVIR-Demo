#!/usr/bin/env python3
"""Chequeo operacional externo simple contra /health/metrics.

Uso:
  python scripts/check_health_metrics.py --url http://localhost:8000/health/metrics
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ELVIR health metrics alert status")
    parser.add_argument("--url", default="http://localhost:8000/health/metrics", help="Metrics endpoint URL")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="HTTP timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--fail-on-alert",
        action="store_true",
        help="Exit with code 1 if any alert flag is true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with urllib.request.urlopen(args.url, timeout=args.timeout_seconds) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - execution-path for ops failures
        print(f"❌ Unable to fetch metrics endpoint: {exc}")
        return 2

    metrics = payload.get("metrics", {})
    alerts = payload.get("alerts", {})
    thresholds = payload.get("thresholds", {})

    print("health_metrics:")
    print(json.dumps({"metrics": metrics, "alerts": alerts, "thresholds": thresholds}, indent=2, ensure_ascii=False))

    active_alerts = [name for name, active in alerts.items() if active]
    if active_alerts:
        print(f"⚠️ Active alerts: {', '.join(active_alerts)}")
        return 1 if args.fail_on_alert else 0

    print("✅ No active alerts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
