from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import CitationModel, DocumentModel


class RetrievalInput(BaseModel):
    citations: list[CitationModel] = Field(default_factory=list)


class RetrievalOutput(BaseModel):
    documents: list[DocumentModel] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)


class RetrievalAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("retrieval", "prompts/retrieval.system.txt")

    def run(self, payload: RetrievalInput) -> RetrievalOutput:
        docs: list[DocumentModel] = []
        failures: list[str] = []
        for c in payload.citations:
            content = (c.abstract or "").strip()
            if not content:
                failures.append(c.citation_id)
                continue
            docs.append(
                DocumentModel(
                    citation_id=c.citation_id,
                    title=c.title,
                    source_url=c.url,
                    content=content,
                )
            )
        out = RetrievalOutput(documents=docs, failures=failures)
        self._log("run", {"documents": len(docs), "failures": len(failures)})
        return out

    def __call__(self, state: dict) -> dict:
        citations = [CitationModel(**c) for c in state.get("validated_citations", [])]
        out = self.run(RetrievalInput(citations=citations))
        return {"documents": [d.model_dump() for d in out.documents], "retrieval_failures": out.failures}
