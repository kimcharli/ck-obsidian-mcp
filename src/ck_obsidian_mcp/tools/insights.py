"""Insight capture tool: writes extracted knowledge to category index notes."""

import re

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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-").lower()
    return slug or "untitled"


def _insight_path(insight: Insight) -> str:
    folder = settings.category_path(insight.category)
    stamp = insight.captured_at.strftime("%Y%m%d-%H%M%S")
    title_slug = _slugify(insight.title)
    return f"{folder}/{stamp}-{insight.session_id}-{title_slug}.md"


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


def _insight_page_content(insight: Insight, emoji: str) -> str:
    tags = "\n".join(f"  - {tag}" for tag in insight.tags)
    tag_block = f"\ntags:\n{tags}" if tags else ""
    return (
        "---\n"
        f"category: {insight.category.value}\n"
        f"title: {insight.title}\n"
        f"session_id: {insight.session_id}\n"
        f"agent: {insight.agent}\n"
        f"captured_at: {insight.captured_at.isoformat()}"
        f"{tag_block}\n"
        "---\n\n"
        f"# {emoji} {insight.title}\n\n"
        f"- **Agent:** {insight.agent}\n"
        f"- **Session:** `{insight.session_id}`\n"
        f"- **Captured:** {insight.captured_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        + (
            "- **Tags:** " + " ".join(f"`#{tag}`" for tag in insight.tags) + "\n"
            if insight.tags
            else ""
        )
        + "\n## Content\n\n"
        + insight.content
        + "\n"
    )


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

    page_path = _insight_path(insight)
    _client.create_note(page_path, _insight_page_content(insight, _CATEGORY_EMOJI[category]))

    emoji = _CATEGORY_EMOJI[category]
    ts = insight.captured_at.strftime("%Y-%m-%d %H:%M UTC")
    tag_str = " ".join(f"`#{t}`" for t in insight.tags) if insight.tags else ""
    page_name = page_path.split("/")[-1]

    block_lines = [
        f"## {emoji} [{insight.title}]({page_name})",
        "",
        f"- **Agent:** {agent}  **Session:** `{session_id}`  **Captured:** {ts}",
        f"- **Page:** `{page_name}`",
    ]
    if tag_str:
        block_lines.append(f"- **Tags:** {tag_str}")
    block_lines += [
        "",
        "See the dedicated page for the full note.",
        "",
        "---",
        "",
    ]

    _client.append_to_note(_index_path(category), "\n".join(block_lines))

    return {
        "ok": True,
        "category": category.value,
        "index_path": _index_path(category),
        "page_path": page_path,
        "title": insight.title,
    }
