from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import OutlineModel


class OutlineValidatorInput(BaseModel):
    merged_outline: OutlineModel
    original_citations: list[str] = Field(default_factory=list)


class OutlineValidatorOutput(BaseModel):
    is_valid: bool
    missing_citations: list[str] = Field(default_factory=list)
    feedback: str = ""


class OutlineValidatorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("outline_validator", "prompts/outline_validator.system.txt")

    def run(self, payload: OutlineValidatorInput) -> OutlineValidatorOutput:
        merged_cites: set[str] = set()
        for sec in payload.merged_outline.sections:
            merged_cites.update(sec.citation_keys)
        missing = sorted(set(payload.original_citations) - merged_cites)
        valid = len(missing) == 0 and len(payload.merged_outline.sections) > 0
        feedback = "Outline valid" if valid else "Missing citation preservation or empty outline"
        out = OutlineValidatorOutput(is_valid=valid, missing_citations=missing, feedback=feedback)
        self._log("run", out.model_dump())
        return out

    def __call__(self, state: dict) -> dict:
        outline = OutlineModel(**state.get("merged_outline", {"title": "State of the Art", "sections": []}))
        original = [c.get("citation_id", "") for c in state.get("validated_citations", []) if c.get("citation_id")]
        out = self.run(OutlineValidatorInput(merged_outline=outline, original_citations=original))
        return {
            "outline_valid": out.is_valid,
            "outline_missing_citations": out.missing_citations,
            "outline_validation_feedback": out.feedback,
        }
