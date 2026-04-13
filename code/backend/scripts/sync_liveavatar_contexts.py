#!/usr/bin/env python3
"""Sync LiveAvatar contexts by name into local mapping (and optionally DB)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "app" / "data"
ROLES_PATH = DATA_DIR / "teleton_roles.json"
CASES_PATH = DATA_DIR / "teleton_cases.json"
OUTPUT_PATH = DATA_DIR / "liveavatar_contexts.json"


def _normalize(text: str) -> str:
    base = unicodedata.normalize("NFKD", text or "")
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = base.lower()
    base = re.sub(r"[^a-z0-9]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    return base


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _split_context_name(name: str) -> tuple[str | None, str | None]:
    parts = re.split(r"\s*-\s*", name or "", maxsplit=1)
    if len(parts) < 2:
        return None, None
    return parts[0].strip(), parts[1].strip()


def _build_role_map(roles: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for slug, payload in roles.items():
        name = payload.get("nombre") or slug
        mapping[_normalize(name)] = slug
        mapping[_normalize(slug.replace("_", " "))] = slug
    return mapping


def _build_case_map(cases: list[dict]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for payload in cases:
        slug = payload.get("slug")
        if not slug:
            continue
        name = payload.get("name") or slug
        mapping[_normalize(name)] = slug
        mapping[_normalize(slug.replace("_", " "))] = slug

    aliases = {
        "apoyo emocional": "apoyo_regulacion_emocional",
        "apoyo regulacion": "apoyo_regulacion_emocional",
        "apoyo regulacion emocional": "apoyo_regulacion_emocional",
        "apoyo regulación": "apoyo_regulacion_emocional",
        "alta estructuracion": "alta_estructuracion_respuesta",
        "alta estructuración": "alta_estructuracion_respuesta",
        "exigencia alta": "exigencia_alta_presentacion_discapacidad",
        "normal": "normal",
    }
    for alias, slug in aliases.items():
        mapping[_normalize(alias)] = slug
    return mapping


# Algunos entornos tienen slugs cortos en la tabla cases (baja/media/alta).
# Este mapa permite actualizar la BD aunque los slugs "largos" no existan.
CASE_DB_ALIASES: dict[str, list[str]] = {
    "normal": ["normal"],
    "apoyo_regulacion_emocional": ["apoyo_regulacion_emocional", "baja"],
    "alta_estructuracion_respuesta": ["alta_estructuracion_respuesta", "media"],
    "exigencia_alta_presentacion_discapacidad": [
        "exigencia_alta_presentacion_discapacidad",
        "alta",
    ],
}


def _fetch_contexts(api_key: str, base_url: str, timeout_s: int = 20) -> list[dict]:
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
            if isinstance(data, dict):
                payload = data.get("data", data)
            else:
                payload = data

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync LiveAvatar contexts by name.")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Ruta de salida del JSON.")
    parser.add_argument("--reset", action="store_true", help="Ignora el JSON actual y recrea el mapa.")
    parser.add_argument("--dry-run", action="store_true", help="No escribe archivo ni BD.")
    parser.add_argument("--apply-db", action="store_true", help="Actualiza los context_id en la BD.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Timeout de lectura para LiveAvatar (segundos).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Reintentos en caso de timeout al consultar LiveAvatar.",
    )
    parser.add_argument(
        "--fail-missing",
        action="store_true",
        help="Retorna código distinto de 0 si faltan combinaciones esperadas.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    from app.config import settings

    if not settings.LIVEAVATAR_API_KEY:
        raise RuntimeError("LIVEAVATAR_API_KEY no está configurada en code/backend/.env")

    roles = _load_json(ROLES_PATH)
    cases = _load_json(CASES_PATH)
    role_map = _build_role_map(roles)
    case_map = _build_case_map(cases)

    current = {} if args.reset else _load_optional_json(Path(args.output))

    attempt = 0
    while True:
        try:
            contexts = _fetch_contexts(
                settings.LIVEAVATAR_API_KEY,
                settings.LIVEAVATAR_API_BASE,
                timeout_s=args.timeout,
            )
            break
        except httpx.TimeoutException:
            if attempt >= args.retries:
                raise
            wait_s = 2**attempt
            print(f"Timeout LiveAvatar (intento {attempt + 1}). Reintentando en {wait_s}s...")
            time.sleep(wait_s)
            attempt += 1

    matched = 0
    skipped = []
    duplicates = []

    for ctx in contexts:
        name = (ctx.get("name") or "").strip()
        ctx_id = _resolve_context_id(ctx)
        if not name or not ctx_id:
            skipped.append({"reason": "missing_name_or_id", "name": name, "id": ctx_id})
            continue
        role_raw, case_raw = _split_context_name(name)
        if not role_raw or not case_raw:
            skipped.append({"reason": "name_format", "name": name, "id": ctx_id})
            continue
        role_slug = role_map.get(_normalize(role_raw))
        case_slug = case_map.get(_normalize(case_raw))
        if not role_slug or not case_slug:
            skipped.append(
                {
                    "reason": "no_match",
                    "name": name,
                    "role_raw": role_raw,
                    "case_raw": case_raw,
                }
            )
            continue

        current.setdefault(role_slug, {})
        existing = current[role_slug].get(case_slug)
        if existing and existing != ctx_id:
            duplicates.append(
                {
                    "role": role_slug,
                    "case": case_slug,
                    "existing": existing,
                    "new": ctx_id,
                    "name": name,
                }
            )
        current[role_slug][case_slug] = ctx_id
        matched += 1

    if not args.dry_run:
        Path(args.output).write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.apply_db and not args.dry_run:
        from app.database import SessionLocal
        from app.models.case import Case
        from app.models.job_role import JobRole
        from app.models.simulation_template import SimulationTemplate

        session = SessionLocal()
        try:
            updated = 0
            missing_tpl = []
            for role_slug, cases_map in current.items():
                role = session.query(JobRole).filter(JobRole.slug == role_slug).first()
                if not role:
                    continue
                for case_slug, ctx_id in cases_map.items():
                    case = session.query(Case).filter(Case.slug == case_slug).first()
                    if not case:
                        for alt_slug in CASE_DB_ALIASES.get(case_slug, []):
                            if alt_slug == case_slug:
                                continue
                            case = session.query(Case).filter(Case.slug == alt_slug).first()
                            if case:
                                break
                    if not case:
                        missing_tpl.append((role_slug, case_slug))
                        continue
                    tpl = (
                        session.query(SimulationTemplate)
                        .filter(
                            SimulationTemplate.job_role_id == role.id,
                            SimulationTemplate.case_id == case.id,
                        )
                        .first()
                    )
                    if not tpl:
                        missing_tpl.append((role_slug, case_slug))
                        continue
                    if tpl.liveavatar_context_id != ctx_id:
                        tpl.liveavatar_context_id = ctx_id
                        updated += 1
            session.commit()
        finally:
            session.close()

        if missing_tpl:
            print(f"Warning: plantillas faltantes: {missing_tpl}")
        print(f"DB actualizado: {updated} plantillas.")

    expected_pairs = {(r, c["slug"]) for r in roles.keys() for c in cases if c.get("slug")}
    current_pairs = {(r, c) for r, cases_map in current.items() for c in cases_map.keys()}
    missing_expected = sorted(expected_pairs - current_pairs)
    extra_pairs = sorted(current_pairs - expected_pairs)

    print(f"Matched: {matched}")
    print(f"Skipped: {len(skipped)}")
    if skipped:
        print("Ejemplos skipped:", skipped[:5])
    if duplicates:
        print(f"Duplicados: {len(duplicates)}")
        print("Ejemplos duplicados:", duplicates[:3])
    if missing_expected:
        print(f"Faltan combinaciones esperadas: {len(missing_expected)}")
        print("Ejemplos faltantes:", missing_expected[:10])
    if extra_pairs:
        print(f"Combinaciones extra en el mapa: {len(extra_pairs)}")
        print("Ejemplos extra:", extra_pairs[:10])

    if args.fail_missing and missing_expected:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
