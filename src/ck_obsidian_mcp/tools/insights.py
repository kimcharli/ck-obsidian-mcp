"""Insight capture tool: writes extracted knowledge to category index notes."""

from __future__ import annotations

from ck_obsidian_mcp.config import AgentName, InsightCategory, settings
from ck_obsidian_mcp.obsidian.client import ObsidianClient
from ck_obsidian_mcp.obsidian.models import Insight

_client = ObsidianClient(settings)

_CATEGORY_EMOJI: dict[InsightCategory, str] = {
    InsightCategory.decision: "🧭",
    InsightCategory.code_snippet: "💻",
    InsightCategory.action_item: "✅",
    InsightCategory.summary: "📋",
    InsightCategory.lesson_learned: "📚",
    InsightCategory.skill: "🛠️",
    InsightCategory.sdd_point: "📐",
    InsightCategory.handoff: "🤝",
    InsightCategory.ddd_skill: "🏗️",
}


def _index_path(category: InsightCategory) -> str:
    folder = settings.category_path(category)
    return f"{folder}/index.md"


def _ensure_index_header(category: InsightCategory) -> None:
    """Create the index note with a header if it doesn't exist yet."""
    path = _index_path(category)
    if not _client.note_exists(path):
        emoji = _CATEGORY_EMOJI[category]
        header = (
            f"# {emoji} {category.value.replace('_', ' ').title()} Index\n\n"
            f"Auto-generated index of captured insights from AI agent sessions.\n\n"
            f"---\n\n"
        )
        _client.create_note(path, header)


def capture_insight(
    session_id: str,
    agent: AgentName,
    category: InsightCategory,
    title: str,
    content: str,
    tags: list[str] | None = None,
) -> dict:
    """Extract and store an insight into the appropriate category index note.

    Each captured insight is appended as a collapsible section to the index.
    """
    insight = Insight(
        category=category,
        title=title,
        content=content,
        session_id=session_id,
        agent=agent,
        tags=tags or [],
    )
    _ensure_index_header(category)

    emoji = _CATEGORY_EMOJI[category]
    ts = insight.captured_at.strftime("%Y-%m-%d %H:%M UTC")
    tag_str = " ".join(f"`#{t}`" for t in insight.tags) if insight.tags else ""

    block_lines = [
        f"## {emoji} {insight.title}",
        "",
        f"- **Agent:** {agent}  **Session:** `{session_id}`  **Captured:** {ts}",
    ]
    if tag_str:
        block_lines.append(f"- **Tags:** {tag_str}")
    block_lines += [
        "",
        insight.content,
        "",
        "---",
        "",
    ]

    _client.append_to_note(_index_path(category), "\n".join(block_lines))

    return {
        "ok": True,
        "category": category.value,
        "index_path": _index_path(category),
        "title": insight.title,
    }
