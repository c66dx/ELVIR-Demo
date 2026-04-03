"""Esquemas para resúmenes cualitativos de entrevistas."""

from pydantic import BaseModel, Field, field_validator

_MAX_SUMMARY_CHARS = 100_000
_MAX_TAGS = 30
_MAX_TAG_LEN = 200


class SummaryRequest(BaseModel):
    summary_text: str = Field(...)
    competency_tags: list[str] | None = Field(None, max_length=_MAX_TAGS)

    @field_validator("summary_text")
    @classmethod
    def summary_nonempty_and_bounded(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("El resumen no puede estar vacío")
        if len(s) > _MAX_SUMMARY_CHARS:
            raise ValueError(f"El resumen no puede superar {_MAX_SUMMARY_CHARS} caracteres")
        return s

    @field_validator("competency_tags")
    @classmethod
    def normalize_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        seen: set[str] = set()
        out: list[str] = []
        for raw in v:
            if not isinstance(raw, str):
                continue
            t = raw.strip()
            if not t or len(t) > _MAX_TAG_LEN:
                continue
            key = t.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
        return out or None
