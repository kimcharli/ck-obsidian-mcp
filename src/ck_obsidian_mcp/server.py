"""MCP server entry point — uses FastMCP for mcp dev / inspector compatibility."""

from __future__ import annotations

import json
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from ck_obsidian_mcp.config import InsightCategory
from ck_obsidian_mcp.tools.insights import capture_insight as _capture_insight
from ck_obsidian_mcp.tools.session import (
    end_session as _end_session,
)
from ck_obsidian_mcp.tools.session import (
    get_last_handoff as _get_last_handoff,
)
from ck_obsidian_mcp.tools.session import (
    list_sessions as _list_sessions,
)
from ck_obsidian_mcp.tools.session import (
    log_message as _log_message,
)
from ck_obsidian_mcp.tools.session import (
    start_session as _start_session,
)

mcp = FastMCP("ck-obsidian-mcp")

_AGENT_DESC = "AI agent type: claude, copilot, gemini, or unknown"
_SID_DESC = "session_id returned by start_session"


# ---------------------------------------------------------------------------
# Session tools
# ---------------------------------------------------------------------------


@mcp.tool()
def start_session(
    agent: Annotated[str, "AI agent type: claude, copilot, gemini, or unknown"],
    project: Annotated[str | None, "Project name — used to look up and link handoff notes"] = None,
    topic: Annotated[str | None, "Brief topic/title for this session"] = None,
    workdir: Annotated[
        str | None,
        "Absolute path of the working directory. "
        "Used for project continuity; last handoff is returned automatically.",
    ] = None,
) -> str:
    """Create a new AI chat session note in Obsidian and return a session_id.

    If project or workdir is provided, the last handoff note is returned as
    'last_handoff' so the agent can immediately resume context.
    """
    return json.dumps(
        _start_session(agent=agent, project=project, topic=topic, workdir=workdir),
        default=str,
        indent=2,
    )


@mcp.tool()
def log_message(
    session_id: Annotated[str, _SID_DESC],
    agent: Annotated[str, _AGENT_DESC],
    role: Annotated[str, "Message sender: 'user' or 'assistant'"],
    content: Annotated[str, "Message content (Markdown supported)"],
) -> str:
    """Append a conversation turn (user or assistant) to the session note."""
    return json.dumps(
        _log_message(session_id=session_id, agent=agent, role=role, content=content),
        default=str,
        indent=2,
    )


@mcp.tool()
def end_session(
    session_id: Annotated[str, _SID_DESC],
    agent: Annotated[str, _AGENT_DESC],
    summary: Annotated[str | None, "High-level summary of the session"] = None,
    handoff_notes: Annotated[
        str | None,
        "Detailed context for the next session: current state, what was completed, "
        "what is in progress, next steps, relevant file paths, open questions.",
    ] = None,
    project: Annotated[str | None, "Project name (match start_session value)"] = None,
    workdir: Annotated[str | None, "Working directory path (match start_session value)"] = None,
) -> str:
    """Finalize the session note. Write handoff_notes to persist context for the next session."""
    return json.dumps(
        _end_session(
            session_id=session_id,
            agent=agent,
            summary=summary,
            handoff_notes=handoff_notes,
            project=project,
            workdir=workdir,
        ),
        default=str,
        indent=2,
    )


@mcp.tool()
def list_sessions(
    agent: Annotated[str | None, "Filter by agent type (optional)"] = None,
    limit: Annotated[int, "Maximum sessions to return"] = 20,
) -> str:
    """List recent AI chat session notes from Obsidian."""
    return json.dumps(_list_sessions(agent=agent, limit=limit), default=str, indent=2)


@mcp.tool()
def get_last_handoff(
    project: Annotated[str | None, "Project name"] = None,
    workdir: Annotated[str | None, "Working directory path"] = None,
) -> str:
    """Retrieve the latest handoff note for a project or workdir.

    Use at the start of a coding session to resume where the last session left off.
    Also returned automatically by start_session when project/workdir is provided.
    """
    return json.dumps(_get_last_handoff(project=project, workdir=workdir), default=str, indent=2)


# ---------------------------------------------------------------------------
# Insight tool
# ---------------------------------------------------------------------------


@mcp.tool()
def capture_insight(
    session_id: Annotated[str, _SID_DESC],
    agent: Annotated[str, _AGENT_DESC],
    category: Annotated[
        str,
        "Knowledge category: decision, code_snippet, action_item, summary, "
        "lesson_learned, skill, sdd_point, handoff, ddd_skill",
    ],
    title: Annotated[str, "Short descriptive title for this insight"],
    content: Annotated[str, "Insight content (Markdown supported)"],
    tags: Annotated[list[str] | None, "Optional tags"] = None,
) -> str:
    """Extract and store an important insight into the appropriate Obsidian index note."""
    return json.dumps(
        _capture_insight(
            session_id=session_id,
            agent=agent,
            category=InsightCategory(category),
            title=title,
            content=content,
            tags=tags,
        ),
        default=str,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
