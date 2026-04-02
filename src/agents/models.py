from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CitationModel(BaseModel):
    citation_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None


class DocumentModel(BaseModel):
    citation_id: str
    title: str
    source_url: str | None = None
    content: str


class SummaryModel(BaseModel):
    citation_id: str
    objective: str
    methodology: str
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: str


class OutlineSectionModel(BaseModel):
    title: str
    subsections: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)


class OutlineModel(BaseModel):
    title: str
    sections: list[OutlineSectionModel] = Field(default_factory=list)


class SectionModel(BaseModel):
    title: str
    subsections: list[str] = Field(default_factory=list)
    citation_keys: list[str] = Field(default_factory=list)
    target_words: int = 1000


class RubricModel(BaseModel):
    dimensions: dict[str, float] = Field(default_factory=dict)
    threshold: float = 4.0


class FeedbackModel(BaseModel):
    dimension: str
    score: float
    comments: str
    section_refs: list[str] = Field(default_factory=list)


class ReviewerOutputModel(BaseModel):
    scores: list[float] = Field(default_factory=list)
    feedback: list[FeedbackModel] = Field(default_factory=list)


class AgentResultModel(BaseModel):
    success: bool = True
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
