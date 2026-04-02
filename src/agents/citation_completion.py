from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import CitationModel


class CitationCompletionInput(BaseModel):
    citations: list[CitationModel] = Field(default_factory=list)
    draft: str = ""


class CitationCompletionOutput(BaseModel):
    bibtex_entries: str
    completed_citations: list[CitationModel] = Field(default_factory=list)


class CitationCompletionAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("citation_completion", "prompts/citation_completion.system.txt")

    def run(self, payload: CitationCompletionInput) -> CitationCompletionOutput:
        entries: list[str] = []
        completed = payload.citations
        for c in completed:
            entries.extend([
                f"@misc{{{c.citation_id},",
                f"  title = {{{c.title}}},",
                f"  author = {{{' and '.join(c.authors) if c.authors else 'Unknown'}}},",
                f"  year = {{{c.year if c.year else 2025}}},",
                f"  howpublished = {{{c.venue if c.venue else 'Unknown venue'}}}",
                "}",
                "",
            ])
        bib = "\n".join(entries).strip() + "\n"
        out = CitationCompletionOutput(bibtex_entries=bib, completed_citations=completed)
        self._log("run", {"entries": len(completed)})
        return out

    def __call__(self, state: dict) -> dict:
        citations = [CitationModel(**c) for c in state.get("validated_citations", [])]
        out = self.run(CitationCompletionInput(citations=citations, draft=state.get("edited_content", state.get("draft", ""))))
        return {
            "bibtex_entries": out.bibtex_entries,
            "completed_citations": [c.model_dump() for c in out.completed_citations],
        }
