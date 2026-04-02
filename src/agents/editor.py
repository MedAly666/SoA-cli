from __future__ import annotations

import re
from pydantic import BaseModel, Field

from .base import BaseAgent


class EditorInput(BaseModel):
    merged_sections: str
    outline: dict = Field(default_factory=dict)


class EditorOutput(BaseModel):
    edited_content: str
    changes_made: list[str] = Field(default_factory=list)


class EditorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("editor", "prompts/editor.system.txt")

    def run(self, payload: EditorInput) -> EditorOutput:
        text = payload.merged_sections
        before = text
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\s+\n", "\n", text)
        changes = []
        if text != before:
            changes.append("normalized_whitespace")
        out = EditorOutput(edited_content=text, changes_made=changes)
        self._log("run", {"changes": changes})
        return out

    def __call__(self, state: dict) -> dict:
        out = self.run(EditorInput(merged_sections=state.get("draft", ""), outline=state.get("merged_outline", {})))
        return {"edited_content": out.edited_content, "editor_changes": out.changes_made}
