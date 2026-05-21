# ck-obsidian-mcp

An MCP server that lets AI agents (Claude, Copilot, Gemini) log their chat sessions directly to your Obsidian vault. Important insights — decisions, code snippets, action items, lessons learned, skills, SDD points, handoffs, and DDD patterns — are automatically indexed into dedicated, searchable notes.

## Features

- 📝 **One note per session** — per agent, per date
- 🧭 **Insight extraction** — 9 categories indexed for retrieval
- 🔌 **stdio transport** — works with Claude Desktop, VS Code MCP, any MCP-compatible host
- ⚙️ **Configurable** — vault path, API URL/key via env vars

## Vault Structure

```txt
AI-Chats/
  Sessions/          ← one note per conversation
  Decisions/         ← key decisions (index.md)
  Code-Snippets/     ← code samples (index.md)
  Action-Items/      ← todos / follow-ups (index.md)
  Summaries/         ← session summaries (index.md)
  Lessons-Learned/   ← fixes, gotchas (index.md)
  Skills/            ← AI agent skills, copilot skills, SDD skills (index.md)
  SDD/               ← SDD critical points (index.md)
  Handoff/           ← handoff procedures (index.md)
  DDD-Skills/        ← domain-driven development patterns (index.md)
```

## Prerequisites

1. **Obsidian** with the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) community plugin installed and enabled
2. **Python 3.14+** and [uv](https://github.com/astral-sh/uv)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/kimcharli/ck-obsidian-mcp
cd ck-obsidian-mcp
uv sync
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your Obsidian REST API key and vault settings
```

Get your API key from: **Obsidian → Settings → Community Plugins → Local REST API → API Key**

### 3. Register with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ck-obsidian-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ck-obsidian-mcp", "ck-obsidian-mcp"],
      "env": {
        "OBSIDIAN_REST_API_URL": "http://localhost:27123",
        "OBSIDIAN_REST_API_KEY": "your-api-key-here",
        "VAULT_ROOT": "AI-Chats"
      }
    }
  }
}
```

### 4. Register with VS Code MCP

The `.mcp.json` file in the project root is pre-configured. Update `OBSIDIAN_REST_API_KEY` with your key.

## MCP Tools

| Tool | Description |
| ------ | ------------- |
| `start_session` | Start a new session note; returns `session_id` |
| `log_message` | Append a user/assistant turn to the session note |
| `end_session` | Close the session with an optional summary |
| `capture_insight` | Save important data to a category index note |
| `list_sessions` | List recent sessions (optionally filtered by agent) |

### Insight categories

| Category | Folder | Use for |
| ---------- | -------- | --------- |
| `decision` | Decisions/ | Architecture and design decisions |
| `code_snippet` | Code-Snippets/ | Reusable code samples |
| `action_item` | Action-Items/ | Follow-up tasks |
| `summary` | Summaries/ | Session summaries |
| `lesson_learned` | Lessons-Learned/ | Fixes, gotchas, post-mortems |
| `skill` | Skills/ | Agent skills, Copilot skills, SDD skills |
| `sdd_point` | SDD/ | Software Design Document critical points |
| `handoff` | Handoff/ | Context for the next agent/session |
| `ddd_skill` | DDD-Skills/ | Domain-Driven Design patterns |

## Example Agent Usage

```python
# At session start
start_session(agent="claude", project="my-app", topic="Auth implementation")
→ { session_id: "a1b2c3d4", note_path: "AI-Chats/Sessions/claude-2026-05-20-a1b2c3d4.md" }

# Log messages
log_message(session_id="a1b2c3d4", agent="claude", role="user", content="How should I implement auth?")
log_message(session_id="a1b2c3d4", agent="claude", role="assistant", content="Use JWT because...")

# Capture a decision
capture_insight(
  session_id="a1b2c3d4", agent="claude",
  category="decision", title="Use JWT for auth",
  content="JWT chosen over sessions — stateless, works across microservices.",
  tags=["auth", "jwt"]
)

# End session
end_session(session_id="a1b2c3d4", agent="claude", summary="Implemented JWT auth flow.")
```

## Development

Canonical guide: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)

```bash
uv sync --extra dev

# Lint + format
uv run ruff check --fix src tests
uv run ruff format src tests

# Tests
uv run pytest

# Install git hooks (run once after clone)
uv run pre-commit install
```

### Specs

Software Design Document lives in [`specs/SDD.md`](specs/SDD.md).

## Configuration Reference

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `OBSIDIAN_REST_API_URL` | `http://localhost:27123` | Local REST API base URL |
| `OBSIDIAN_REST_API_KEY` | *(required)* | API key from the plugin |
| `VAULT_ROOT` | `AI-Chats` | Root folder in the vault |
