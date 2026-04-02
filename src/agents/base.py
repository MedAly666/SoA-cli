from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.llm_client import LLMClient


class BaseAgent:
    """Common utilities for all SoA-CLI agents."""

    def __init__(self, name: str, prompt_file: str) -> None:
        self.name = name
        self.prompt_file = Path(prompt_file)
        self.log_path = Path("artifacts/soa/logs") / f"{name}.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_prompt(self) -> str:
        if self.prompt_file.exists():
            return self.prompt_file.read_text(encoding="utf-8")
        return ""

    def _log(self, event: str, payload: dict[str, Any]) -> None:
        record = {
            "ts": datetime.utcnow().isoformat(),
            "agent": self.name,
            "event": event,
            "payload": payload,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _call_llm(self, user_payload: dict[str, Any], timeout: int = 120) -> str:
        """Best-effort LLM call; callers should keep deterministic fallbacks."""
        system_prompt = self._load_prompt()
        if not system_prompt:
            return ""
        client = LLMClient(timeout=timeout)
        return client.call(system_prompt, json.dumps(user_payload, ensure_ascii=False, indent=2))
