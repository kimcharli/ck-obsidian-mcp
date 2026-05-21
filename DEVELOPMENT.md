# Development Guide

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- Obsidian with the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin (for end-to-end testing)

## Setup

```bash
git clone https://github.com/kimcharli/ck-obsidian-mcp
cd ck-obsidian-mcp
uv sync --extra dev
cp .env.example .env       # edit with your Obsidian REST API key
uv run pre-commit install  # install git hooks
```

## Running the Server

```bash
# stdio mode (production — used by Claude Desktop / VS Code)
uv run ck-obsidian-mcp

# or directly
uv run python -m ck_obsidian_mcp.server
```

## Linting & Formatting

```bash
uv run ruff check --fix src tests
uv run ruff format src tests
```

Pre-commit hooks run these automatically on `git commit`.

## Testing

```bash
# All tests (httpx-mocked, no Obsidian needed)
uv run pytest

# Verbose with output
uv run pytest -v -s

# Single test
uv run pytest tests/test_tools.py::TestSessionTools::test_start_session
```

## Interactive Debugging with MCP Inspector

The fastest way to exercise all tools manually against a live Obsidian vault:

```bash
uv run mcp dev src/ck_obsidian_mcp/server.py
```

Opens the MCP Inspector UI at **[http://localhost:5173](http://localhost:5173)**.

- Select a tool from the left panel
- Fill in the JSON arguments
- Click **Run** — response appears on the right
- Check your Obsidian vault to confirm notes were created

> **Requires:** Obsidian open, Local REST API plugin enabled, `.env` with a valid `OBSIDIAN_REST_API_KEY`.

## Debugging Tool Calls via stdio

Send raw JSON-RPC to the server over stdin to test without an MCP host:

```bash
# List all registered tools
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' \
  | uv run ck-obsidian-mcp

# Call start_session
echo '{"jsonrpc":"2.0","method":"tools/call","id":2,"params":{"name":"start_session","arguments":{"agent":"claude","project":"debug-test"}}}' \
  | uv run ck-obsidian-mcp
```

## Debugging with Claude Desktop

1. Add the server to `~/Library/Application Support/Claude/claude_desktop_config.json` (see `claude_desktop_config.example.json`)
2. Restart Claude Desktop
3. Open **Claude Desktop → Settings → Developer → MCP Servers** to verify the server is connected
4. Ask Claude: *"Use the ck-obsidian-mcp tools to start a session for project 'test'."*
5. Check `~/Library/Logs/Claude/mcp-server-ck-obsidian-mcp.log` for server-side logs

## Debugging with VS Code / Copilot

1. Ensure `.mcp.json` in the project root has your API key set
2. Open the MCP output panel: **View → Output → MCP**
3. Reload the MCP server via the Command Palette: `MCP: Restart Server`

## Common Issues

### `401 Unauthorized` from Obsidian REST API

- Confirm Obsidian is running and the Local REST API plugin is enabled
- Check `OBSIDIAN_REST_API_KEY` in `.env` matches the key shown in:
  **Obsidian → Settings → Community Plugins → Local REST API**

### `404` when appending to a note

`ObsidianClient.append_to_note` catches 404 and falls back to `create_note` automatically. If you see persistent 404s, the vault path may be wrong — check `VAULT_ROOT` in `.env`.

### `Session <id> not found` error

`_find_session_note` scans `AI-Chats/Sessions/` for a file matching both `session_id` and `agent`. If the Sessions folder is empty or the listing fails (e.g. Obsidian not running), this error is returned.

### MCP Inspector shows "not a valid server object"

The inspector requires a `FastMCP` instance. `server.py` exports `mcp` (a `FastMCP` object) — make sure you haven't reverted to the old low-level `Server` class.

### `uv run mcp dev` picks up wrong Python

Run `uv python list` to verify 3.14 is available. If not: `uv python install 3.14`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_REST_API_URL` | `http://localhost:27123` | Base URL of the Local REST API plugin |
| `OBSIDIAN_REST_API_KEY` | *(required)* | Bearer token from the plugin settings |
| `VAULT_ROOT` | `AI-Chats` | Root folder inside the Obsidian vault |

## Project Layout

```text
src/ck_obsidian_mcp/
  server.py          FastMCP entry point; all tool registrations
  config.py          Settings (pydantic-settings) + InsightCategory enum + CATEGORY_FOLDER map
  tools/
    session.py       start_session, log_message, end_session, list_sessions,
                     get_last_handoff + handoff note helpers
    insights.py      capture_insight → category index notes
  obsidian/
    client.py        ObsidianClient (httpx) — create/append/get/list notes
    models.py        Pydantic models: SessionMetadata, Message, Insight
specs/
  SDD.md             Software Design Document
tests/
  test_tools.py      pytest + pytest-httpx tests (no live Obsidian needed)
```

## Adding a New Tool

1. Implement the logic in `src/ck_obsidian_mcp/tools/`
2. Register with `@mcp.tool()` in `server.py`
3. Add a test in `tests/test_tools.py`
4. Update `specs/SDD.md` Section 4 (MCP Tools)
