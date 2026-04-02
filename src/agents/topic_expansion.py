from __future__ import annotations

from pydantic import BaseModel, Field

from .base import BaseAgent


class TopicExpansionInput(BaseModel):
    topic: str
    max_subtopics: int = 10


class TopicExpansionOutput(BaseModel):
    subtopics: list[str] = Field(default_factory=list)
    confidence_scores: list[float] = Field(default_factory=list)


class TopicExpansionAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("topic_expansion", "prompts/topic_expansion.system.txt")

    def run(self, payload: TopicExpansionInput) -> TopicExpansionOutput:
        base = payload.topic.strip()
        stems = [
            "foundations",
            "taxonomy",
            "methodologies",
            "benchmarks and datasets",
            "evaluation metrics",
            "limitations",
            "future directions",
            "applications",
            "theoretical analysis",
            "systems and deployment",
        ]
        subtopics = [f"{base}: {s}" for s in stems[: max(1, payload.max_subtopics)]]
        scores = [round(max(0.5, 0.95 - i * 0.03), 2) for i in range(len(subtopics))]
        out = TopicExpansionOutput(subtopics=subtopics, confidence_scores=scores)
        self._log("run", out.model_dump())
        return out

    def __call__(self, state: dict) -> dict:
        inp = TopicExpansionInput(topic=state.get("topic", ""), max_subtopics=state.get("max_subtopics", 10))
        out = self.run(inp)
        return {"subtopics": out.subtopics, "subtopic_confidence_scores": out.confidence_scores}
