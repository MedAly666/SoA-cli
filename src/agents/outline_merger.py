from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import OutlineModel, OutlineSectionModel


class OutlineMergerInput(BaseModel):
    partial_outlines: list[OutlineModel] = Field(default_factory=list)


class OutlineMergerOutput(BaseModel):
    merged_outline: OutlineModel


class OutlineMergerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("outline_merger", "prompts/outline_merger.system.txt")

    def run(self, payload: OutlineMergerInput) -> OutlineMergerOutput:
        if not payload.partial_outlines:
            merged = OutlineModel(title="State of the Art", sections=[])
            return OutlineMergerOutput(merged_outline=merged)

        title = payload.partial_outlines[0].title
        section_map: dict[str, OutlineSectionModel] = {}
        for outline in payload.partial_outlines:
            for sec in outline.sections:
                if sec.title not in section_map:
                    section_map[sec.title] = OutlineSectionModel(
                        title=sec.title,
                        subsections=list(sec.subsections),
                        citation_keys=list(sec.citation_keys),
                    )
                else:
                    existing = section_map[sec.title]
                    existing.subsections = sorted(set(existing.subsections + sec.subsections))
                    existing.citation_keys = sorted(set(existing.citation_keys + sec.citation_keys))

        merged = OutlineModel(title=title, sections=list(section_map.values()))
        out = OutlineMergerOutput(merged_outline=merged)
        self._log("run", {"sections": len(merged.sections)})
        return out

    def __call__(self, state: dict) -> dict:
        outlines = [OutlineModel(**o) for o in state.get("partial_outlines", [])]
        out = self.run(OutlineMergerInput(partial_outlines=outlines))
        return {"merged_outline": out.merged_outline.model_dump()}
