#!/usr/bin/env python3
"""Publish LiveAvatar contexts from generated prompt files (create/update)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data"
ROLES_PATH = DATA_DIR / "teleton_roles.json"
CASES_PATH = DATA_DIR / "teleton_cases.json"


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No se encontro el archivo: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _find_teleton_dir(root: Path) -> Path:
    candidates = [root.parent / "material", root.parent.parent / "material", root.parent.parent.parent / "material"]
    material_dir = next((p for p in candidates if p.exists()), None)
    if not material_dir:
        raise FileNotFoundError("No se encontro carpeta material/ en niveles superiores.")
    for p in material_dir.iterdir():
        if p.is_dir() and p.name.lower().startswith("tele"):
            return p
    raise FileNotFoundError("No se encontro carpeta Teletón dentro de material/")


def _fetch_contexts(api_key: str, base_url: str, timeout_s: int = 30) -> list[dict]:
    url = base_url.rstrip("/") + "/contexts"
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
    }
    items: list[dict] = []
    with httpx.Client(timeout=timeout_s) as client:
        while url:
            resp = client.get(url, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"LiveAvatar /contexts {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            payload = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(payload, dict):
                page_items = payload.get("results") or payload.get("items") or payload.get("contexts")
                if not isinstance(page_items, list):
                    raise RuntimeError("Respuesta de LiveAvatar no contiene lista de contexts.")
                items.extend([item for item in page_items if isinstance(item, dict)])
                url = payload.get("next")
                continue
            if isinstance(payload, list):
                items.extend([item for item in payload if isinstance(item, dict)])
                url = None
                continue
            raise RuntimeError("Respuesta de LiveAvatar no contiene lista de contexts.")
    return items


def _resolve_context_id(item: dict) -> str | None:
    return item.get("id") or item.get("context_id") or item.get("_id")


def _load_prompt_files(source_dir: Path) -> dict[tuple[str, str], Path]:
    pattern = re.compile(r"^prompt_(?P<role>.+)_(?P<case>.+)\\.txt$", re.IGNORECASE)
    mapping: dict[tuple[str, str], Path] = {}
    for path in source_dir.iterdir():
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if not match:
            continue
        role = match.group("role").strip().lower()
        case = match.group("case").strip().lower()
        mapping[(role, case)] = path
    return mapping


def _build_name_map(roles: dict, cases: list[dict]) -> dict[tuple[str, str], str]:
    role_names = {slug: payload.get("nombre") or slug for slug, payload in roles.items()}
    case_names = {item["slug"]: item.get("name") or item["slug"] for item in cases if item.get("slug")}
    return {(r, c): f"{role_names[r]} - {case_names[c]}" for r in role_names for c in case_names}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish LiveAvatar contexts from prompt files.")
    parser.add_argument("--source-dir", default="", help="Carpeta con prompt_*.txt (output_prompts_v2).")
    parser.add_argument("--opening-file", default="", help="Archivo con saludo (opening.txt).")
    parser.add_argument(
        "--mode",
        choices=["create", "update", "upsert"],
        default="upsert",
        help="create: solo crea; update: solo actualiza; upsert: crea o actualiza.",
    )
    parser.add_argument("--dry-run", action="store_true", help="No crea ni actualiza en LiveAvatar.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout para llamadas HTTP.")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    from app.config import settings

    if not settings.LIVEAVATAR_API_KEY:
        raise RuntimeError("LIVEAVATAR_API_KEY no esta configurada en code/backend/.env")

    teleton_dir = _find_teleton_dir(ROOT)
    source_dir = Path(args.source_dir) if args.source_dir else (teleton_dir / "output_prompts_v2")
    opening_file = Path(args.opening_file) if args.opening_file else (source_dir / "opening.txt")

    if not source_dir.exists():
        raise FileNotFoundError(f"No se encontro source-dir: {source_dir}")
    if not opening_file.exists():
        raise FileNotFoundError(f"No se encontro opening-file: {opening_file}")

    roles = _load_json(ROLES_PATH)
    cases = _load_json(CASES_PATH)
    name_map = _build_name_map(roles, cases)
    prompt_files = _load_prompt_files(source_dir)

    opening_text = opening_file.read_text(encoding="utf-8").strip()
    base_url = settings.LIVEAVATAR_API_BASE.rstrip("/")
    headers = {"X-API-KEY": settings.LIVEAVATAR_API_KEY, "Content-Type": "application/json"}

    existing = _fetch_contexts(settings.LIVEAVATAR_API_KEY, settings.LIVEAVATAR_API_BASE, timeout_s=args.timeout)
    existing_by_name = {item.get("name"): _resolve_context_id(item) for item in existing if item.get("name")}

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    with httpx.Client(timeout=args.timeout) as client:
        for (role_slug, case_slug), ctx_name in name_map.items():
            prompt_path = prompt_files.get((role_slug, case_slug))
            if not prompt_path:
                errors.append(f"Falta prompt: {role_slug}/{case_slug} en {source_dir}")
                continue

            prompt_text = prompt_path.read_text(encoding="utf-8").strip()
            payload = {"name": ctx_name, "prompt": prompt_text, "opening_text": opening_text}

            ctx_id = existing_by_name.get(ctx_name)

            if ctx_id and args.mode == "create":
                skipped += 1
                continue
            if not ctx_id and args.mode == "update":
                skipped += 1
                continue

            if args.dry_run:
                print(f"[dry-run] {args.mode} {ctx_name}")
                continue

            try:
                if ctx_id:
                    resp = client.patch(f"{base_url}/contexts/{ctx_id}", headers=headers, json=payload)
                    if resp.status_code >= 400:
                        errors.append(f"PATCH {ctx_name}: {resp.status_code} {resp.text[:200]}")
                        continue
                    updated += 1
                else:
                    resp = client.post(f"{base_url}/contexts", headers=headers, json=payload)
                    if resp.status_code >= 400:
                        errors.append(f"POST {ctx_name}: {resp.status_code} {resp.text[:200]}")
                        continue
                    created += 1
            except httpx.TimeoutException:
                errors.append(f"Timeout {ctx_name}")

    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    if errors:
        print(f"Errors: {len(errors)}")
        print("Ejemplos:", errors[:5])
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
