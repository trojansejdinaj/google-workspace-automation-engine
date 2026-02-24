from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParseError:
    code: str
    message: str
    field: str | None = None
    span: tuple[int, int] | None = None


@dataclass
class ParsedEmail:
    fields: dict[str, object]
    confidence: float
    errors: list[ParseError]
