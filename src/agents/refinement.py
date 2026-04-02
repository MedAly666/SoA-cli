from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import FeedbackModel


class RefinementInput(BaseModel):
    draft: str
    feedback: list[FeedbackModel] = Field(default_factory=list)
    ckm_context: str = ""


class RefinementOutput(BaseModel):
    revised_draft: str
    revision_plan: str


class RefinementAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("refinement", "prompts/refinement.system.txt")

    def run(self, payload: RefinementInput) -> RefinementOutput:
        low_dims = [f.dimension for f in payload.feedback if f.score < 4.0]
        plan = "No major revisions required." if not low_dims else f"Improve sections for: {', '.join(low_dims)}"
        revision_note = "\n\n## Revision Notes\n\n" + plan + "\n"
        revised = payload.draft.strip() + revision_note
        out = RefinementOutput(revised_draft=revised, revision_plan=plan)
        self._log("run", {"low_dimensions": low_dims})
        return out

    def __call__(self, state: dict) -> dict:
        fb = [FeedbackModel(**f) for f in state.get("review_feedback", [])]
        draft = state.get("edited_content", state.get("draft", ""))
        out = self.run(RefinementInput(draft=draft, feedback=fb, ckm_context=state.get("ckm_context", "")))
        current_round = int(state.get("refinement_round", 0))
        return {
            "edited_content": out.revised_draft,
            "revision_plan": out.revision_plan,
            "refinement_round": current_round + 1,
        }
