# Software Design Document — ck-obsidian-mcp

<!-- markdownlint-disable MD060 -->

## 1. Overview

`ck-obsidian-mcp` is a Python MCP (Model Context Protocol) server that enables AI agents (Claude, Copilot, Gemini) to log their chat sessions and extracted knowledge to an Obsidian vault via the [Local REST API plugin](https://github.com/coddingtonbear/obsidian-local-rest-api).

### Goals

- Provide a standardized MCP interface for AI agents to persist conversational context
- Structure session logs and extracted insights for later retrieval in Obsidian
- Support multiple agent types through a single, configurable server

### Non-Goals

- Real-time streaming of messages (agents batch-log turns)
- Obsidian plugin development
- Chat UI or replay functionality

---

## 2. Architecture

```text
┌──────────────────────────────────────────────────────────┐
│  AI Agent (Claude / Copilot / Gemini)                    │
│  MCP Host (Claude Desktop / VS Code / Gemini CLI)        │
└────────────────────┬─────────────────────────────────────┘
                     │ MCP stdio transport
                     ▼
┌──────────────────────────────────────────────────────────┐
│  ck-obsidian-mcp (this server)                           │
│                                                          │
│  ┌─────────────────┐   ┌─────────────────────────────┐  │
│  │  MCP Tools      │   │  ObsidianClient (httpx)     │  │
│  │  session.py     │──▶│  PUT / PATCH / GET          │  │
│  │  insights.py    │   │  /vault/<path>              │  │
│  └─────────────────┘   └──────────────┬──────────────┘  │
│                                        │ HTTP            │
└────────────────────────────────────────┼─────────────────┘
                                         ▼
                          Obsidian Local REST API plugin
                          (localhost:27123)
                                         │
                                         ▼
                               Obsidian Vault (filesystem)
```

---

## 3. Module Structure

```txt
src/ck_obsidian_mcp/
  server.py          MCP entry point; registers tools, runs stdio loop
  config.py          Settings (pydantic-settings); InsightCategory enum
  tools/
    session.py       start_session, log_message, end_session, list_sessions, get_last_handoff
    insights.py      capture_insight
  obsidian/
    client.py        ObsidianClient — create_note, append_to_note, list_notes
    models.py        Pydantic models: SessionMetadata, Message, Insight
specs/
  SDD.md             This document
tests/
  test_tools.py      pytest + pytest-httpx integration tests
```

---

## 4. MCP Tools

### 4.1 `start_session`

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `agent` | `"claude"\|"copilot"\|"gemini"\|"unknown"` | ✓ | Agent type |
| `project` | string | — | Project context |
| `topic` | string | — | Session topic/title |

**Returns:** `{ session_id, note_path, agent }`

Creates `AI-Chats/Sessions/<agent>-<date>-<id>.md` with YAML frontmatter.

---

### 4.2 `log_message`

| Param | Type | Required |
|-------|------|----------|
| `session_id` | string | ✓ |
| `agent` | AgentName | ✓ |
| `role` | `"user"\|"assistant"` | ✓ |
| `content` | string | ✓ |

Appends a formatted message block to the session note.

---

### 4.3 `end_session`

| Param | Type | Required |
|-------|------|----------|
| `session_id` | string | ✓ |
| `agent` | AgentName | ✓ |
| `summary` | string | — |

Appends a `## Session End` block with timestamp and optional summary.

---

### 4.4 `capture_insight`

| Param | Type | Required |
|-------|------|----------|
| `session_id` | string | ✓ |
| `agent` | AgentName | ✓ |
| `category` | InsightCategory | ✓ |
| `title` | string | ✓ |
| `content` | string | ✓ |
| `tags` | list[str] | — |

`capture_insight` is the MCP entry point for consolidating durable knowledge.
Use it for reusable best practices, lessons learned, decisions, handoff
context, and other information that should live beyond a single session.
`log_message` remains the raw conversation transcript and should not be used
for curated knowledge capture.

**Categories and vault folders:**

| Category | Vault Folder | Emoji | Purpose |
|----------|-------------|-------|---------|
| `decision` | Decisions/ | 🧭 | Architecture / design choices |
| `code_snippet` | Code-Snippets/ | 💻 | Reusable code |
| `action_item` | Action-Items/ | ✅ | Follow-up tasks |
| `summary` | Summaries/ | 📋 | Session summaries |
| `lesson_learned` | Lessons-Learned/ | 📚 | Fixes, gotchas |
| `skill` | Skills/ | 🛠️ | Agent / Copilot / SDD skills |
| `sdd_point` | SDD/ | 📐 | SDD critical points |
| `handoff` | Handoff/ | 🤝 | Context for next session |
| `ddd_skill` | DDD-Skills/ | 🏗️ | Domain-Driven Design patterns |

Each captured insight is stored as a dedicated page inside the matching category folder, and the category's `index.md` acts as a collection page that links to the individual insight pages.

**Page layout:**

- Category index: `AI-Chats/<CategoryFolder>/index.md`
- Insight page: `AI-Chats/<CategoryFolder>/<timestamp>-<session_id>-<slug>.md`

The page contains the full note content and metadata, while the index keeps the short, scannable collection of links.

---

### 4.5 `list_sessions`

| Param | Type | Required |
|-------|------|----------|
| `agent` | AgentName | — |
| `limit` | int (default 20) | — |

---

### 4.6 `get_last_handoff`

| Param | Type | Required |
|-------|------|----------|
| `project` | string | ✓ or workdir |
| `workdir` | string | ✓ or project |

**Returns:** `{ found, handoff_key, content? }`

Fetches the latest handoff note for the given project/workdir. Also returned automatically by `start_session` when `project` or `workdir` is supplied.

---

## 5. Project Continuity (Coding Agent Workflows)

Coding agents such as **Claude Code**, **Gemini CLI**, and **Copilot** operate in a working directory and carry significant context (files open, current task, recent changes, blockers). Without explicit handoff, each new session starts cold. This section defines how `ck-obsidian-mcp` maintains continuity across sessions.

### 5.1 Concept

```text
Session N                           Session N+1
──────────────────────────          ──────────────────────────
start_session(workdir=…)            start_session(workdir=…)
  → no handoff found (first)          → last_handoff returned ✓
…work…                              Agent reads handoff, resumes
end_session(handoff_notes=…)        …continues work…
  → writes Handoff/<slug>.md         end_session(handoff_notes=…)
```

### 5.2 Handoff Note Location

```text
AI-Chats/Handoff/<project-slug>.md
```

The slug is derived from the `project` name, or from the basename of `workdir` if no project is set. Special characters are replaced with `-`. Examples:

| Input | Slug | Path |
|-------|------|------|
| `project="my-app"` | `my-app` | `Handoff/my-app.md` |
| `workdir="/Users/ckim/Projects/ck-obsidian-mcp"` | `ck-obsidian-mcp` | `Handoff/ck-obsidian-mcp.md` |

Only **one handoff note per project** is maintained — it is **overwritten** on each `end_session` call so the file always contains the latest state.

### 5.3 Handoff Note Format

```markdown
---
handoff_key: my-app
last_session_id: a1b2c3d4
last_agent: claude
last_updated: 2026-05-20T23:30:00+00:00
project: my-app
workdir: /Users/ckim/Projects/my-app
---

# 🤝 Handoff — my-app

> Last updated by **claude** on 2026-05-20 23:30 UTC (session `a1b2c3d4`)

**Project:** my-app
**Workdir:** `/Users/ckim/Projects/my-app`

## Summary

Implemented JWT auth flow with refresh tokens.

## Handoff Notes

### Current State
- `src/auth/jwt.py` — complete, tests passing
- `src/auth/refresh.py` — in progress, ~60% done

### Next Steps
1. Finish `refresh_token()` in `src/auth/refresh.py`
2. Add integration test in `tests/test_auth.py`
3. Update OpenAPI spec in `docs/api.yaml`

### Open Questions
- Should refresh tokens be stored in Redis or PostgreSQL?

### Key Files
- `/Users/ckim/Projects/my-app/src/auth/` — auth module
- `/Users/ckim/Projects/my-app/tests/test_auth.py` — auth tests
```

### 5.4 Agent Workflow — Coding Session

**At session start:**

```python
# Agent calls:
start_session(agent="claude", project="my-app", workdir="/Users/ckim/Projects/my-app")

# Response includes last_handoff if one exists:
{
  "session_id": "b2c3d4e5",
  "note_path": "AI-Chats/Sessions/claude-2026-05-20-b2c3d4e5.md",
  "agent": "claude",
  "last_handoff": "# 🤝 Handoff — my-app\n...",
  "handoff_key": "my-app"
}
# Agent reads last_handoff and resumes context immediately.
```

**At session end:**

```python
end_session(
    session_id="b2c3d4e5",
    agent="claude",
    project="my-app",
    workdir="/Users/ckim/Projects/my-app",
    summary="Completed refresh token implementation.",
    handoff_notes="""
### Current State
- `src/auth/refresh.py` — complete, all tests passing

### Next Steps
1. Update OpenAPI spec in `docs/api.yaml`
2. Deploy to staging

### Key Files
- `src/auth/` — complete auth module
- `tests/test_auth.py` — all tests green
"""
)
# Response includes handoff_path confirming where it was saved.
```

### 5.5 Recommended Handoff Notes Content

Agents should include:

- **Current state** — which files/features are complete, in progress, or blocked
- **Next steps** — ordered list of concrete tasks to pick up
- **Open questions** — unresolved decisions or blockers
- **Key files** — absolute paths to the most relevant files
- **Environment notes** — any env vars, local services, or credentials context needed

---

## 6. Vault Structure & Note Format

### 6.1 Folder Layout

The default layout under `VAULT_ROOT` (default: `AI-Chats`) is:

```txt
AI-Chats/
  Sessions/          ← one note per conversation
  Decisions/         ← index.md
  Code-Snippets/     ← index.md
  Action-Items/      ← index.md
  Summaries/         ← index.md
  Lessons-Learned/   ← index.md
  Skills/            ← index.md
  SDD/               ← index.md
  Handoff/           ← <project-slug>.md per project
  DDD-Skills/        ← index.md
```

> **Folder flexibility:** Any folder or subfolder in this layout can be **created, renamed, or deleted** to match your personal vault organization. The mapping from insight category → folder is defined in `config.py` (`CATEGORY_FOLDER`) and `VAULT_ROOT` is set via the `VAULT_ROOT` env var — update either to reflect structural changes. The Obsidian REST API creates intermediate directories automatically when a note path is written, so no manual folder creation is needed.

### 6.2 Session note (`Sessions/<agent>-<date>-<id>.md`)

```markdown
---
session_id: a1b2c3d4
agent: claude
started_at: 2026-05-20T23:15:00+00:00
project: my-app
topic: Auth implementation
status: active
---

# Claude Session — 2026-05-20 23:15 UTC
**Project:** my-app
**Topic:** Auth implementation

## Conversation

### 🧑 User — 23:15 UTC

How should I implement auth?

### 🤖 Claude — 23:15 UTC

Use JWT because...

## Session End — 2026-05-20 23:30 UTC

**Summary:** Implemented JWT auth flow.
**Status:** closed
```

### 6.3 Category index note (`<Category>/index.md`)

```markdown
# 🧭 Decision Index

Auto-generated index of captured insights from AI agent sessions.

---

## 🧭 Use JWT for auth

- **Agent:** claude  **Session:** `a1b2c3d4`  **Captured:** 2026-05-20 23:20 UTC
- **Tags:** `#auth` `#security`

JWT chosen over sessions — stateless, works across microservices.

---
```

---

## 7. Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `OBSIDIAN_REST_API_URL` | `http://localhost:27123` | REST API base URL |
| `OBSIDIAN_REST_API_KEY` | *(required)* | Bearer token from plugin |
| `VAULT_ROOT` | `AI-Chats` | Root folder in vault |

---

## 8. Error Handling

- All tool handlers wrap logic in `try/except`; errors returned as `{ "error": "..." }` JSON
- `ObsidianClient.append_to_note` falls back to `create_note` on 404
- Missing session notes return `{ "error": "Session <id> not found" }`

---

## 9. Toolchain

| Tool | Purpose |
|------|---------|
| Python 3.14 | Runtime |
| uv | Package management, virtual env |
| ruff | Lint + format |
| pre-commit | Git hook enforcement |
| pytest + pytest-httpx | Testing with mocked HTTP |

---

## 10. Open Questions / Future Work

- [ ] Support for Obsidian tags on session notes (derived from project/topic)
- [ ] Periodic insight summarization (roll-up weekly digest note)
- [ ] `search_insights` tool to query index notes by keyword
- [ ] Support for SSE/HTTP transport in addition to stdio
