from pydantic import BaseModel


class PromptInput(BaseModel):
    alumno_id: str | None = None
    cargo_id: str | None = None
    case_id: str | None = None
    session_id: int | None = None
    grafo_state: dict | None = None
    metadata: dict | None = None


class PromptResult(BaseModel):
    prompt: str
    opening_text: str | None = None
    name: str | None = None
    provider: str = "endpoint"
    version: str | None = None
    raw: dict | None = None


class EvaluationInput(BaseModel):
    alumno_id: str | None = None
    session_id: int | None = None
    transcript: str
    metadata: dict | None = None


class EvaluationResult(BaseModel):
    snapshot: dict | None = None
    provider: str = "endpoint"
    version: str | None = None
    raw: dict | None = None
