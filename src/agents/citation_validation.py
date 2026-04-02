from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import CitationModel


class CitationValidationInput(BaseModel):
    citations: list[CitationModel] = Field(default_factory=list)


class CitationValidationOutput(BaseModel):
    validated_citations: list[CitationModel] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CitationValidationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("citation_validation", "prompts/citation_validation.system.txt")

    def run(self, payload: CitationValidationInput) -> CitationValidationOutput:
        seen: set[str] = set()
        out: list[CitationModel] = []
        errors: list[str] = []
        for c in payload.citations:
            key = (c.title or "").strip().lower()
            if not key:
                errors.append(f"missing_title:{c.citation_id}")
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        result = CitationValidationOutput(validated_citations=out, errors=errors)
        self._log("run", {"validated": len(out), "errors": len(errors)})
        return result

    def __call__(self, state: dict) -> dict:
        citations = [CitationModel(**c) for c in state.get("citations", [])]
        out = self.run(CitationValidationInput(citations=citations))
        return {
            "validated_citations": [c.model_dump() for c in out.validated_citations],
            "citation_validation_errors": out.errors,
        }
