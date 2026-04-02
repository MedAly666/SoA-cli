from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import SummaryModel


class CKMInput(BaseModel):
    summaries: list[SummaryModel] = Field(default_factory=list)
    query_citation_keys: list[str] = Field(default_factory=list)


class CKMOutput(BaseModel):
    memory_entries: dict[str, SummaryModel] = Field(default_factory=dict)
    injected_context: str = ""


class CKMManagerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("ckm_manager", "prompts/ckm_manager.system.txt")

    def run(self, payload: CKMInput) -> CKMOutput:
        memory = {s.citation_id: s for s in payload.summaries}
        keys = payload.query_citation_keys or list(memory.keys())
        selected = [memory[k] for k in keys if k in memory]
        context = "\n\n".join([f"[{s.citation_id}] {s.summary}" for s in selected])
        out = CKMOutput(memory_entries=memory, injected_context=context)
        self._log("run", {"entries": len(memory), "injected": len(selected)})
        return out

    def __call__(self, state: dict) -> dict:
        summaries = [SummaryModel(**s) for s in state.get("summaries", [])]
        out = self.run(CKMInput(summaries=summaries, query_citation_keys=state.get("query_citation_keys", [])))
        return {
            "ckm_memory": {k: v.model_dump() for k, v in out.memory_entries.items()},
            "ckm_context": out.injected_context,
        }
