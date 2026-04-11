"""Ensambla el prompt para LiveAvatar (formato Teletón)."""

from pathlib import Path

from app.models.case import Case
from app.models.job_role import JobRole

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
ROL_PATH = PROMPTS_DIR / "rol.txt"
ESTRUCTURA_PATH = PROMPTS_DIR / "estructura.txt"
INDICACIONES_BASE = (
    "Toda la interacción debe centrarse en capacidades, competencias y formas de desempeño "
    "en el puesto de trabajo."
)


def _load_txt(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{label} no encontrado: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_rol() -> str:
    """Carga el texto del rol del avatar."""
    return _load_txt(ROL_PATH, "Rol")


def load_estructura() -> str:
    """Carga la estructura base de la entrevista."""
    return _load_txt(ESTRUCTURA_PATH, "Estructura")


def _cargo_text(job_role: JobRole) -> str:
    return (job_role.description or job_role.objetivo or job_role.name or "").strip()


def _indicaciones_text(case: Case) -> str:
    return (case.prompt_instructions or "").strip()


def build_prompt(job_role: JobRole, case: Case) -> str:
    """Ensambla el prompt completo según formato Teletón."""
    rol = load_rol()
    estructura = load_estructura()
    cargo = _cargo_text(job_role)
    indicaciones = _indicaciones_text(case)
    indicaciones_block = (
        f"{INDICACIONES_BASE}\n{indicaciones}" if indicaciones else INDICACIONES_BASE
    )

    sections = [
        "# ROL DEL AVATAR\n" + rol,
        "# CARGO AL QUE SE ORIENTA LA ENTREVISTA\n" + cargo,
        "# ESTRUCTURA DE LA ENTREVISTA\n" + estructura,
        "# INDICACIONES GENERALES PARA LA ENTREVISTA\n" + indicaciones_block,
    ]
    return "\n\n".join(sections)
