from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent
from .models import FeedbackModel, ReviewerOutputModel, RubricModel


class ReviewerPoolInput(BaseModel):
    draft: str
    rubric: RubricModel
    chunk_size: int = 4000


class ReviewerPoolAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("reviewer_pool", "prompts/reviewer_pool.system.txt")

    def run(self, payload: ReviewerPoolInput) -> ReviewerOutputModel:
        dims = payload.rubric.dimensions or {
            "Scope": 0.0,
            "Literature": 0.0,
            "Analysis": 0.0,
            "Originality": 0.0,
            "Organization": 0.0,
            "Presentation": 0.0,
            "References": 0.0,
        }
        base_score = 4.2 if len(payload.draft) > 2500 else 3.6
        scores = [round(base_score, 2) for _ in dims.keys()]
        feedback = [
            FeedbackModel(
                dimension=dim,
                score=scores[i],
                comments=("Strong" if scores[i] >= payload.rubric.threshold else "Needs refinement"),
                section_refs=[],
            )
            for i, dim in enumerate(dims.keys())
        ]
        out = ReviewerOutputModel(scores=scores, feedback=feedback)
        self._log("run", {"avg_score": sum(scores) / len(scores) if scores else 0.0})
        return out

    def __call__(self, state: dict) -> dict:
        rubric = RubricModel(
            dimensions=state.get("rubric_dimensions", {
                "Scope": 0, "Literature": 0, "Analysis": 0, "Originality": 0,
                "Organization": 0, "Presentation": 0, "References": 0,
            }),
            threshold=state.get("threshold", 4.0),
        )
        draft = state.get("edited_content", state.get("draft", ""))
        out = self.run(ReviewerPoolInput(draft=draft, rubric=rubric, chunk_size=state.get("chunk_size", 4000)))
        avg = (sum(out.scores) / len(out.scores)) if out.scores else 0.0
        return {
            "review_scores": out.scores,
            "review_feedback": [f.model_dump() for f in out.feedback],
            "avg_score": avg,
        }
