from enum import StrEnum
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InsightCategory(StrEnum):
    decision = "decision"
    code_snippet = "code_snippet"
    action_item = "action_item"
    summary = "summary"
    lesson_learned = "lesson_learned"
    skill = "skill"
    sdd_point = "sdd_point"
    handoff = "handoff"
    ddd_skill = "ddd_skill"


CATEGORY_FOLDER: dict[InsightCategory, str] = {
    InsightCategory.decision: "Decisions",
    InsightCategory.code_snippet: "Code-Snippets",
    InsightCategory.action_item: "Action-Items",
    InsightCategory.summary: "Summaries",
    InsightCategory.lesson_learned: "Lessons-Learned",
    InsightCategory.skill: "Skills",
    InsightCategory.sdd_point: "SDD",
    InsightCategory.handoff: "Handoff",
    InsightCategory.ddd_skill: "DDD-Skills",
}

AgentName = Literal["claude", "copilot", "gemini", "unknown"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    obsidian_rest_api_url: str = Field(
        default="http://localhost:27123",
        description="Base URL of the Obsidian REST API plugin",
    )
    obsidian_rest_api_key: str = Field(
        default="",
        description="API key for the Obsidian REST API plugin",
    )
    vault_root: str = Field(
        default="AI-Chats",
        description="Root folder inside the Obsidian vault for all AI chat logs",
    )

    @property
    def sessions_path(self) -> str:
        return f"{self.vault_root}/Sessions"

    def category_path(self, category: InsightCategory) -> str:
        folder = CATEGORY_FOLDER[category]
        return f"{self.vault_root}/{folder}"


settings = Settings()
