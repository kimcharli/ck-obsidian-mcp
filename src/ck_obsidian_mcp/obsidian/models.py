from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ck_obsidian_mcp.config import AgentName, InsightCategory


class SessionMetadata(BaseModel):
    session_id: str
    agent: AgentName
    started_at: datetime
    project: str | None = None
    topic: str | None = None
    workdir: str | None = None


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Insight(BaseModel):
    category: InsightCategory
    title: str
    content: str
    session_id: str
    agent: AgentName
    tags: list[str] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=datetime.utcnow)
