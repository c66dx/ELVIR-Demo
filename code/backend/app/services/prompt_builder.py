"""Ensambla el prompt para LiveAvatar (Opción B: catálogo en BD)."""
import json
from pathlib import Path

from app.models.job_role import JobRole
from app.models.case import Case


PROMPT_BASE_PATH = Path(__file__).parent.parent / "prompts" / "prompt_base.txt"


def load_prompt_base() -> str:
    """Carga el prompt base (persona Javiera, estructura)."""
    if not PROMPT_BASE_PATH.exists():
        raise FileNotFoundError(f"Prompt base no encontrado: {PROMPT_BASE_PATH}")
    return PROMPT_BASE_PATH.read_text(encoding="utf-8").strip()


def build_role_context(job_role: JobRole) -> str:
    """Construye el bloque de contexto del cargo."""
    competencias = job_role.competencias
    if isinstance(competencias, str) and competencias:
        try:
            comp_list = json.loads(competencias) if competencias.startswith("[") else [competencias]
        except json.JSONDecodeError:
            comp_list = [competencias]
    else:
        comp_list = competencias if isinstance(competencias, list) else []

    comp_text = "\n- ".join(comp_list) if comp_list else "(sin especificar)"

    return f"""
CONTEXTO DEL PUESTO
Cargo: {job_role.name}
Descripción: {job_role.description or "(sin descripción)"}
Objetivo del rol: {job_role.objetivo or "(sin especificar)"}

Competencias:
- {comp_text}
"""


def build_case_context(case: Case) -> str:
    """Construye el bloque de instrucciones del caso."""
    instructions = case.prompt_instructions or "Entrevista estándar. Mantener tono profesional y empático."
    return f"""
CASO DE ENTREVISTA
Debes ajustar tu estilo de entrevista estrictamente según los siguientes lineamientos.

{instructions}
"""


def build_prompt(job_role: JobRole, case: Case) -> str:
    """Ensambla el prompt completo: base + cargo + caso."""
    base = load_prompt_base()
    role_ctx = build_role_context(job_role)
    case_ctx = build_case_context(case)
    return f"{base}\n\n====================================\n{role_ctx}\n====================================\n{case_ctx}"

