"""Session management tools: start_session, log_message, end_session, list_sessions."""

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from ck_obsidian_mcp.config import AgentName, settings
from ck_obsidian_mcp.obsidian.client import ObsidianClient
from ck_obsidian_mcp.obsidian.models import Message, SessionMetadata

_client = ObsidianClient(settings)


def _session_path(session_id: str, agent: AgentName, started_at: datetime) -> str:
    date_str = started_at.strftime("%Y-%m-%d")
    return f"{settings.sessions_path}/{agent}-{date_str}-{session_id}.md"


def _frontmatter(meta: SessionMetadata) -> str:
    lines = [
        "---",
        f"session_id: {meta.session_id}",
        f"agent: {meta.agent}",
        f"started_at: {meta.started_at.isoformat()}",
    ]
    if meta.project:
        lines.append(f"project: {meta.project}")
    if meta.topic:
        lines.append(f"topic: {meta.topic}")
    if meta.workdir:
        lines.append(f"workdir: {meta.workdir}")
    lines += ["status: active", "---", ""]
    return "\n".join(lines)


def start_session(
    agent: AgentName,
    project: str | None = None,
    topic: str | None = None,
    workdir: str | None = None,
) -> dict:
    """Create a new session note and return the session_id and note path.

    If *workdir* or *project* is provided, the last handoff note for that
    project/workdir is fetched and returned as ``last_handoff`` so the agent
    can immediately resume context from the previous session.
    """
    session_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(UTC)
    meta = SessionMetadata(
        session_id=session_id,
        agent=agent,
        started_at=started_at,
        project=project,
        topic=topic,
        workdir=workdir,
    )
    path = _session_path(session_id, agent, started_at)

    header_parts = [f"# {agent.capitalize()} Session — {started_at.strftime('%Y-%m-%d %H:%M UTC')}"]
    if project:
        header_parts.append(f"**Project:** {project}")
    if topic:
        header_parts.append(f"**Topic:** {topic}")
    if workdir:
        header_parts.append(f"**Workdir:** `{workdir}`")
    header_parts.append("\n## Conversation\n")

    content = _frontmatter(meta) + "\n".join(header_parts)
    _client.create_note(path, content)

    result: dict = {"session_id": session_id, "note_path": path, "agent": agent}

    # Auto-pickup last handoff for continuity
    handoff_key = _handoff_key(project, workdir)
    if handoff_key:
        last = _read_handoff(handoff_key)
        if last:
            result["last_handoff"] = last
            result["handoff_key"] = handoff_key

    return result


def log_message(session_id: str, agent: AgentName, role: str, content: str) -> dict:
    """Append a conversation message to the session note."""
    msg = Message(role=role, content=content)
    timestamp = msg.timestamp.strftime("%H:%M UTC")
    role_label = "🧑 User" if role == "user" else f"🤖 {agent.capitalize()}"
    block = f"\n### {role_label} — {timestamp}\n\n{content}\n"

    # Find the note by scanning for matching session_id prefix in Sessions folder
    note_path = _find_session_note(session_id, agent)
    if not note_path:
        return {"error": f"Session {session_id} not found"}

    _client.append_to_note(note_path, block)
    return {"ok": True, "note_path": note_path}


def end_session(
    session_id: str,
    agent: AgentName,
    summary: str | None = None,
    handoff_notes: str | None = None,
    project: str | None = None,
    workdir: str | None = None,
) -> dict:
    """Finalize a session note and optionally write a handoff for the next session.

    *handoff_notes* should describe the current state of the project: what was
    done, what is in progress, next steps, relevant file paths, and any context
    the next agent session needs to continue without repeating history.
    The handoff is stored as ``AI-Chats/Handoff/<project-slug>.md`` and is
    automatically returned when the next session calls ``start_session`` with
    the same *project* or *workdir*.
    """
    note_path = _find_session_note(session_id, agent)
    if not note_path:
        return {"error": f"Session {session_id} not found"}

    ended_at = datetime.now(UTC)
    block_lines = [f"\n## Session End — {ended_at.strftime('%Y-%m-%d %H:%M UTC')}\n"]
    if summary:
        block_lines.append(f"**Summary:** {summary}\n")
    if handoff_notes:
        block_lines.append(f"**Handoff:**\n\n{handoff_notes}\n")
    block_lines.append("**Status:** closed\n")

    _client.append_to_note(note_path, "\n".join(block_lines))

    result: dict = {"ok": True, "note_path": note_path, "ended_at": ended_at.isoformat()}

    # Persist handoff note for next session pickup
    if handoff_notes:
        handoff_key = _handoff_key(project, workdir)
        if handoff_key:
            _write_handoff(
                key=handoff_key,
                session_id=session_id,
                agent=agent,
                project=project,
                workdir=workdir,
                ended_at=ended_at,
                content=handoff_notes,
                summary=summary,
            )
            result["handoff_path"] = _handoff_path(handoff_key)

    return result


def list_sessions(agent: AgentName | None = None, limit: int = 20) -> dict:
    """List recent session notes, optionally filtered by agent."""
    try:
        files = _client.list_notes(settings.sessions_path)
    except Exception as exc:
        return {"error": str(exc), "sessions": []}

    sessions = []
    for f in files:
        if not f.endswith(".md"):
            continue
        name = f.split("/")[-1].replace(".md", "")  # e.g. claude-2026-05-20-abc12345
        parts = name.split("-")
        if len(parts) < 2:
            continue
        file_agent = parts[0]
        if agent and file_agent != agent:
            continue
        sessions.append({"file": f, "agent": file_agent, "name": name})

    sessions = sessions[-limit:]
    return {"sessions": sessions, "count": len(sessions)}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _find_session_note(session_id: str, agent: AgentName) -> str | None:
    """Return the vault path of a session note given its session_id."""
    try:
        files = _client.list_notes(settings.sessions_path)
    except Exception:
        return None
    for f in files:
        candidate = f if "/" in f else f"{settings.sessions_path}/{f}"
        if session_id in candidate and agent in candidate:
            return candidate
    return None


# ------------------------------------------------------------------
# Project continuity / handoff helpers
# ------------------------------------------------------------------


def _handoff_key(project: str | None, workdir: str | None) -> str | None:
    """Derive a filesystem-safe slug to key handoff notes by project/workdir."""
    raw = project or (Path(workdir).name if workdir else None)
    if not raw:
        return None
    return re.sub(r"[^a-zA-Z0-9._-]", "-", raw).strip("-").lower()


def _handoff_path(key: str) -> str:
    return f"{settings.vault_root}/Handoff/{key}.md"


def _write_handoff(
    key: str,
    session_id: str,
    agent: AgentName,
    project: str | None,
    workdir: str | None,
    ended_at: datetime,
    content: str,
    summary: str | None = None,
) -> None:
    """Overwrite the handoff note so the latest state is always at the top."""
    ts = ended_at.strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "---",
        f"handoff_key: {key}",
        f"last_session_id: {session_id}",
        f"last_agent: {agent}",
        f"last_updated: {ended_at.isoformat()}",
    ]
    if project:
        lines.append(f"project: {project}")
    if workdir:
        lines.append(f"workdir: {workdir}")
    lines += ["---", ""]

    body = [
        f"# 🤝 Handoff — {key}",
        "",
        f"> Last updated by **{agent}** on {ts} (session `{session_id}`)",
        "",
    ]
    if project:
        body.append(f"**Project:** {project}  ")
    if workdir:
        body.append(f"**Workdir:** `{workdir}`  ")
    body.append("")
    if summary:
        body += ["## Summary", "", summary, ""]
    body += ["## Handoff Notes", "", content, ""]

    _client.create_note(_handoff_path(key), "\n".join(lines) + "\n".join(body))


def _read_handoff(key: str) -> str | None:
    """Return the raw Markdown content of the handoff note, or None if absent."""
    try:
        return _client.get_note(_handoff_path(key))
    except Exception:
        return None


def get_last_handoff(
    project: str | None = None,
    workdir: str | None = None,
) -> dict:
    """Return the latest handoff note for a project or workdir.

    Agents should call this at the start of a coding session (or pass
    *project*/*workdir* to ``start_session``, which fetches it automatically).
    """
    key = _handoff_key(project, workdir)
    if not key:
        return {"error": "Provide at least one of: project, workdir"}
    content = _read_handoff(key)
    if content is None:
        return {"found": False, "handoff_key": key}
    return {"found": True, "handoff_key": key, "content": content}
