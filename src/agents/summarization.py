from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import DocumentModel, SummaryModel


class SummarizationInput(BaseModel):
    documents: list[DocumentModel] = Field(default_factory=list)


class SummarizationOutput(BaseModel):
    summaries: list[SummaryModel] = Field(default_factory=list)


class SummarizationAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("summarization", "prompts/summarization.system.txt")

    def run(self, payload: SummarizationInput) -> SummarizationOutput:
        summaries: list[SummaryModel] = []
        for d in payload.documents:
            summaries.append(
                SummaryModel(
                    citation_id=d.citation_id,
                    objective=f"Summarize {d.title}",
                    methodology="Evidence extraction",
                    key_findings=[d.content[:180]],
                    limitations=["Limited metadata in retrieved abstract"],
                    summary=d.content[:500],
                )
            )
        out = SummarizationOutput(summaries=summaries)
        self._log("run", {"summaries": len(summaries)})
        return out

    def __call__(self, state: dict) -> dict:
        docs = [DocumentModel(**d) for d in state.get("documents", [])]
        out = self.run(SummarizationInput(documents=docs))
        return {"summaries": [s.model_dump() for s in out.summaries]}
