from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import CitationModel


class CitationRetrievalInput(BaseModel):
    subtopics: list[str] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)
    max_papers: int = 100


class CitationRetrievalOutput(BaseModel):
    citations: list[CitationModel] = Field(default_factory=list)


class CitationRetrievalAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("citation_retrieval", "prompts/citation_retrieval.system.txt")

    def run(self, payload: CitationRetrievalInput) -> CitationRetrievalOutput:
        citations: list[CitationModel] = []
        idx = 1
        for sub in payload.subtopics:
            if len(citations) >= payload.max_papers:
                break
            citations.append(
                CitationModel(
                    citation_id=f"ref{idx:03d}",
                    title=f"{sub} - Representative Study",
                    authors=["Unknown"],
                    year=2024,
                    venue=(payload.venues[0] if payload.venues else "arXiv"),
                    url=None,
                    abstract=f"Survey evidence placeholder for {sub}.",
                )
            )
            idx += 1
        out = CitationRetrievalOutput(citations=citations)
        self._log("run", {"count": len(out.citations)})
        return out

    def __call__(self, state: dict) -> dict:
        venues = []
        for vs in (state.get("venue_mapping") or {}).values():
            venues.extend(vs)
        out = self.run(
            CitationRetrievalInput(
                subtopics=state.get("subtopics", []),
                venues=sorted(set(venues)),
                max_papers=state.get("max_papers", 100),
            )
        )
        return {"citations": [c.model_dump() for c in out.citations]}
