from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import OutlineModel


class SectionWriterInput(BaseModel):
    section_outline: dict = Field(default_factory=dict)
    ckm_context: str = ""
    citation_keys: list[str] = Field(default_factory=list)


class SectionWriterOutput(BaseModel):
    draft: str
    citations_used: list[str] = Field(default_factory=list)


class SectionWriterAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("section_writer", "prompts/section_writer.system.txt")

    def run(self, payload: SectionWriterInput) -> SectionWriterOutput:
        title = payload.section_outline.get("title", "State of the Art")
        lines = [f"# {title}", "", "## Abstract", "", "This survey synthesizes evidence across the selected literature set."]
        for sec in payload.section_outline.get("sections", []):
            lines.extend(["", f"## {sec.get('title', 'Section')}"])
            for sub in sec.get("subsections", []):
                lines.extend(["", f"### {sub}"])
                cite = sec.get("citation_keys", payload.citation_keys)[:2]
                cite_str = " ".join([f"[@{c}]" for c in cite]) if cite else ""
                lines.append(
                    "This subsection provides evidence-grounded synthesis of methodologies, findings, and limitations "
                    f"for this theme {cite_str}."
                )
        draft = "\n".join(lines).strip() + "\n"
        used = sorted(set(payload.citation_keys + [c for sec in payload.section_outline.get("sections", []) for c in sec.get("citation_keys", [])]))
        out = SectionWriterOutput(draft=draft, citations_used=used)
        self._log("run", {"chars": len(draft), "citations_used": len(used)})
        return out

    def __call__(self, state: dict) -> dict:
        outline = OutlineModel(**state.get("merged_outline", {"title": "State of the Art", "sections": []})).model_dump()
        cite_keys = [c.get("citation_id", "") for c in state.get("validated_citations", []) if c.get("citation_id")]
        out = self.run(SectionWriterInput(section_outline=outline, ckm_context=state.get("ckm_context", ""), citation_keys=cite_keys))
        return {"draft": out.draft, "citations_used": out.citations_used}
