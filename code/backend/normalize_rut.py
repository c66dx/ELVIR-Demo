"""Normaliza valores de RUT para jovenes.

Uso:
  python normalize_rut.py --dry-run
  python normalize_rut.py --apply
  python normalize_rut.py --apply --clear-invalid
"""
from __future__ import annotations

import argparse
import re

from app.database import SessionLocal
from app.models.youth import Youth


def _format_rut_body(body: str) -> str:
    parts = []
    while body:
        parts.append(body[-3:])
        body = body[:-3]
    return ".".join(reversed(parts))


def _compute_rut_dv(body: str) -> str:
    total = 0
    multiplier = 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    mod = 11 - (total % 11)
    if mod == 11:
        return "0"
    if mod == 10:
        return "K"
    return str(mod)


def normalize_rut(value: str) -> str:
    cleaned = re.sub(r"[^0-9kK]", "", value or "").upper()
    if len(cleaned) < 2:
        raise ValueError("invalid")
    body = cleaned[:-1]
    dv = cleaned[-1]
    if not body.isdigit():
        raise ValueError("invalid")
    expected = _compute_rut_dv(body)
    if expected != dv:
        raise ValueError("invalid")
    return f"{_format_rut_body(body)}-{dv}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize RUT values for youths")
    parser.add_argument("--apply", action="store_true", help="Apply changes to the database")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--clear-invalid", action="store_true", help="Clear invalid RUTs (set to NULL)")
    args = parser.parse_args()

    if not args.apply and not args.dry_run:
        args.dry_run = True

    db = SessionLocal()
    try:
        youths: list[Youth] = db.query(Youth).filter(Youth.rut.isnot(None)).all()
        total = len(youths)
        valid_items = []
        invalid_items = []

        for y in youths:
            raw = (y.rut or "").strip()
            if not raw:
                invalid_items.append((y, "empty"))
                continue
            try:
                normalized = normalize_rut(raw)
                valid_items.append((y, normalized))
            except ValueError:
                invalid_items.append((y, "invalid"))

        # Detectar duplicados despues de normalizar
        norm_map: dict[str, list[Youth]] = {}
        for y, norm in valid_items:
            norm_map.setdefault(norm, []).append(y)

        updates = []
        conflicts = []
        for y, norm in valid_items:
            if len(norm_map[norm]) > 1:
                conflicts.append((y, norm))
                continue
            if (y.rut or "").strip() != norm:
                updates.append((y, norm))

        print(f"Total with RUT: {total}")
        print(f"Valid: {len(valid_items)}")
        print(f"Invalid: {len(invalid_items)}")
        print(f"To update: {len(updates)}")
        print(f"Conflicts: {len(conflicts)}")

        if conflicts:
            print("Conflicts (same normalized RUT):")
            for y, norm in conflicts:
                print(f"- youth_id={y.id} rut={y.rut} normalized={norm}")

        if invalid_items:
            print("Invalid RUTs:")
            for y, reason in invalid_items:
                print(f"- youth_id={y.id} rut={y.rut} reason={reason}")

        if args.apply:
            for y, norm in updates:
                y.rut = norm
            if args.clear_invalid:
                for y, _reason in invalid_items:
                    y.rut = None
            db.commit()
            print("Changes applied.")
        else:
            db.rollback()
            print("Dry run: no changes applied.")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
