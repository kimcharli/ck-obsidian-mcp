"""Insight capture tool: writes extracted knowledge to category index notes."""

import hashlib
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


def _normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        clean = tag.strip().lstrip("#")
        if not clean or clean in seen:
            continue
        seen.add(clean)
        normalized.append(clean)
    return normalized


def _compose_content(content: str | None, summary: str | None, details: str | None) -> str:
    summary_text = (summary or "").strip()
    details_text = (details or "").strip()
    content_text = (content or "").strip()

    if summary_text:
        if details_text:
            return f"{summary_text}\n\n## Details\n\n{details_text}"
        return summary_text
    if content_text:
        return content_text
    return details_text


def _insight_content_hash(category: InsightCategory, title: str, content: str) -> str:
    normalized = " ".join(f"{category.value}|{title}|{content}".lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def capture_insight(
    session_id: str,
    agent: AgentName,
    category: InsightCategory,
    title: str,
    content: str | None = None,
    summary: str | None = None,
    details: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Extract and store an insight into the appropriate category index note.

    Each captured insight is appended as a collapsible section to the index.
    """
    raw_content = _compose_content(content=content, summary=summary, details=details)
    if not raw_content:
        return {
            "ok": False,
            "error": "Provide at least one of: content, summary, details",
        }

    original_tags = _normalize_tags(tags)
    stored_tags = original_tags[: settings.max_insight_tags]
    tags_were_truncated = len(stored_tags) < len(original_tags)

    max_chars = settings.max_insight_content_chars
    original_chars = len(raw_content)
    was_truncated = original_chars > max_chars
    stored_content = raw_content
    if was_truncated:
        stored_content = raw_content[:max_chars].rstrip() + "\n\n[... truncated ...]"

    insight = Insight(
        category=category,
        title=title,
        content=stored_content,
        session_id=session_id,
        agent=agent,
        tags=stored_tags,
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
        "content_hash": _insight_content_hash(category=category, title=title, content=raw_content),
        "was_truncated": was_truncated,
        "original_chars": original_chars,
        "stored_chars": len(stored_content),
        "tags_were_truncated": tags_were_truncated,
        "original_tag_count": len(original_tags),
        "stored_tag_count": len(stored_tags),
    }
