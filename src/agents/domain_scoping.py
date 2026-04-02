from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent


class DomainScopingInput(BaseModel):
    subtopics: list[str] = Field(default_factory=list)


class DomainScopingOutput(BaseModel):
    venue_mapping: dict[str, list[str]] = Field(default_factory=dict)


class DomainScopingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("domain_scoping", "prompts/domain_scoping.system.txt")

    def run(self, payload: DomainScopingInput) -> DomainScopingOutput:
        default_venues = ["arXiv", "Semantic Scholar", "IEEE Xplore", "ACM Digital Library", "SpringerLink"]
        mapping = {s: default_venues[:5] for s in payload.subtopics}
        out = DomainScopingOutput(venue_mapping=mapping)
        self._log("run", out.model_dump())
        return out

    def __call__(self, state: dict) -> dict:
        out = self.run(DomainScopingInput(subtopics=state.get("subtopics", [])))
        return {"venue_mapping": out.venue_mapping}
