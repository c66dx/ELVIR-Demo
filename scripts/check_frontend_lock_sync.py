#!/usr/bin/env python3
"""Fail when package.json deps are not mirrored in package-lock root metadata."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "code/frontend/package.json"
LOCK = ROOT / "code/frontend/package-lock.json"


def main() -> int:
    pkg = json.loads(PKG.read_text())
    lock = json.loads(LOCK.read_text())

    pkg_dev = pkg.get("devDependencies", {})
    pkg_deps = pkg.get("dependencies", {})
    lock_root = lock.get("packages", {}).get("", {})
    lock_dev = lock_root.get("devDependencies", {})
    lock_deps = lock_root.get("dependencies", {})

    missing = []
    mismatch = []

    for name, version in pkg_deps.items():
        current = lock_deps.get(name)
        if current is None:
            missing.append(f"dependencies:{name}")
        elif current != version:
            mismatch.append(f"dependencies:{name} package={version} lock={current}")

    for name, version in pkg_dev.items():
        current = lock_dev.get(name)
        if current is None:
            missing.append(f"devDependencies:{name}")
        elif current != version:
            mismatch.append(f"devDependencies:{name} package={version} lock={current}")

    if missing or mismatch:
        print("❌ package-lock.json is not aligned with package.json")
        if missing:
            print("Missing entries:")
            for item in missing:
                print(f" - {item}")
        if mismatch:
            print("Version mismatches:")
            for item in mismatch:
                print(f" - {item}")
        print("Run npm install (or npm install --package-lock-only) in code/frontend and commit both files.")
        return 1

    print("✅ package-lock.json is aligned with package.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
