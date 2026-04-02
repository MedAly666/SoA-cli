from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import OutlineModel, OutlineSectionModel, SummaryModel


class OutlineDrafterInput(BaseModel):
    summaries: list[SummaryModel] = Field(default_factory=list)
    topic: str


class OutlineDrafterOutput(BaseModel):
    partial_outlines: list[OutlineModel] = Field(default_factory=list)


class OutlineDrafterAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("outline_drafter", "prompts/outline_drafter.system.txt")

    def run(self, payload: OutlineDrafterInput) -> OutlineDrafterOutput:
        cite_keys = [s.citation_id for s in payload.summaries][:12]
        sections = [
            OutlineSectionModel(title="Introduction", subsections=["Background", "Scope"], citation_keys=cite_keys[:3]),
            OutlineSectionModel(title="Taxonomy", subsections=["Method Families", "Comparative Axes"], citation_keys=cite_keys[3:6]),
            OutlineSectionModel(title="Comparative Analysis", subsections=["Performance", "Complexity"], citation_keys=cite_keys[6:9]),
            OutlineSectionModel(title="Cross-Cutting Synthesis", subsections=["Consensus", "Contradictions"], citation_keys=cite_keys[9:12]),
            OutlineSectionModel(title="Research Gaps", subsections=["Methodological", "Practical"], citation_keys=cite_keys[:4]),
            OutlineSectionModel(title="Future Directions", subsections=["Near-term", "Long-term"], citation_keys=cite_keys[4:8]),
            OutlineSectionModel(title="Conclusion", subsections=["Summary", "Implications"], citation_keys=cite_keys[8:12]),
        ]
        partial = OutlineModel(title=f"State of the Art: {payload.topic}", sections=sections)
        out = OutlineDrafterOutput(partial_outlines=[partial])
        self._log("run", {"sections": len(sections)})
        return out

    def __call__(self, state: dict) -> dict:
        summaries = [SummaryModel(**s) for s in state.get("summaries", [])]
        out = self.run(OutlineDrafterInput(summaries=summaries, topic=state.get("topic", "Survey")))
        return {"partial_outlines": [o.model_dump() for o in out.partial_outlines]}
