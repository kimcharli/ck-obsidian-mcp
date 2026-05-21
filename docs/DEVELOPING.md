# DEVELOPING.md — Debugging & Development Guide

## Setup

```bash
uv sync --extra dev
uv run pre-commit install
```

Copy `.env.example` to `.env` and fill in your Obsidian REST API credentials (see [Install and enable the Local REST API plugin](#2-install-and-enable-the-local-rest-api-plugin) below).

---

## Setting Up the Obsidian Vault

### 1. Create (or choose) a vault

Open Obsidian and create a vault — for example at `~/Obsidian-Vaults/AI-Chats`:

- Launch Obsidian → **Open another vault → Create new vault**
- Name: `AI-Chats`
- Location: `~/Obsidian-Vaults/` → creates `~/Obsidian-Vaults/AI-Chats/`

> **Which vault is used?** The Local REST API plugin always operates on the **currently open vault**. There is no vault path setting in this project — just ensure the right vault is open in Obsidian before using the MCP server.
>
> `VAULT_ROOT` in `.env` only controls the **subfolder inside the vault** where notes are written (default: `AI-Chats`). It is not the vault's filesystem path.

### 2. Install and enable the Local REST API plugin

1. In Obsidian: **Settings → Community plugins → Turn off Restricted Mode** (if prompted)
2. Click **Browse** and search for **"Local REST API"** (by Adam Coddington)
3. Install and **Enable** the plugin
4. Open **Settings → Local REST API**:
   - Note the **Port** and whether **HTTPS** is enabled (many installs use HTTPS on port `27124`)
   - Copy the **API Key** — copy the **raw token only**, do NOT include any Bearer prefix

### 3. Configure this MCP server

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Use https:// if HTTPS is enabled in the plugin (common default: port 27124)
OBSIDIAN_REST_API_URL=https://localhost:27124
OBSIDIAN_REST_API_KEY=<raw token only — no "Bearer " prefix>
VAULT_ROOT=AI-Chats   # subfolder inside the vault (not the vault path)
```

### 4. Verify the connection

```bash
# Use -k to allow the self-signed cert; use https:// if HTTPS is enabled
curl -sk -H "Authorization: Bearer <your-key>" https://localhost:27124/vault/ | python3 -m json.tool
```

A JSON listing of vault files confirms the plugin is running and the key is correct.

> **Note**: Obsidian must be running with the vault open and the Local REST API plugin active whenever the MCP server makes vault calls.

---

## Running the Server

```bash
# stdio (production mode, for MCP clients)
uv run python -m ck_obsidian_mcp.server

# MCP Inspector (interactive browser UI)
uv run mcp dev src/ck_obsidian_mcp/server.py
```

---

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

---

## Tests

```bash
uv run pytest -v
```

---

## MCP Inspector Walkthrough

1. Run `uv run mcp dev src/ck_obsidian_mcp/server.py`
2. Open the URL shown (typically `http://localhost:5173`)
3. In the **Tools** tab you can call any tool with custom parameters
4. Responses are shown inline; errors appear in the browser console and terminal

> **Requirement**: The server entry point must expose a `FastMCP` instance named `mcp`, `server`, or `app` at module level. The low-level `mcp.server.Server` class is not supported by `mcp dev`.

---

## Raw stdio Debugging

Send JSON-RPC manually over stdin to verify tool dispatch:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | uv run python -m ck_obsidian_mcp.server
```

---

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/Users/yourname/Projects/ck-obsidian-mcp",
        "ck-obsidian-mcp"
      ],
      "env": {
        "OBSIDIAN_REST_API_URL": "http://localhost:27123",
        "OBSIDIAN_REST_API_KEY": "your-key-here"
      }
    }
  }
}
```

Restart Claude Desktop after editing. Check `~/Library/Logs/Claude/mcp-server-obsidian.log` for errors.

---

## VS Code (Copilot) Integration

`.mcp.json` in the project root is already configured. In VS Code settings enable:

```json
"github.copilot.chat.mcp.enabled": true
```

Reload the window. The server will start automatically when a chat session opens.

---

## Gemini CLI Integration

```json
// ~/.gemini/settings.json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/Users/yourname/Projects/ck-obsidian-mcp",
        "ck-obsidian-mcp"
      ]
    }
  }
}
```

---

## Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `server object is of type <class 'module'>` | `mcp` is a module import, not a `FastMCP` instance | Rename the local import; expose `mcp = FastMCP(...)` at module level |
| `Low level Server class is not yet supported` | Using `mcp.server.lowlevel.server.Server` | Switch to `FastMCP` |
| `No server object found` | `mcp dev` can't locate the FastMCP instance | Ensure the variable is named `mcp`, `server`, or `app` and is a module-level global |
| `ConnectionRefusedError` on Obsidian calls | Obsidian REST API plugin not running | Open Obsidian, enable the Local REST API plugin, check it's on port 27123 |
| `401 Unauthorized` | Wrong API key or Bearer prefix in key | Re-copy the raw token only (no Bearer prefix) from Obsidian plugin settings into `.env` |
| `404` on PATCH (append) | Note doesn't exist yet | Handled automatically by `append_to_note` — falls back to PUT (create) |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_REST_API_URL` | `http://localhost:27123` | Obsidian Local REST API base URL — use `https://localhost:27124` if HTTPS is enabled in the plugin |
| `OBSIDIAN_REST_API_KEY` | *(required)* | API key from the plugin settings |
| `VAULT_ROOT` | `AI-Chats` | Root folder inside the vault for all MCP notes |

---

## Project Layout

```txt
ck-obsidian-mcp/
  src/ck_obsidian_mcp/
    server.py         ← FastMCP entry point; all tools registered here
    config.py         ← Settings, InsightCategory, CATEGORY_FOLDER
    tools/
      session.py      ← start_session, log_message, end_session, list_sessions, get_last_handoff
      insights.py     ← capture_insight
    obsidian/
      client.py       ← ObsidianClient (httpx)
      models.py       ← SessionMetadata, Message, Insight
  docs/
    DEVELOPING.md     ← this file
  specs/
    SDD.md            ← Software Design Document
  tests/
    test_tools.py
```

---

## Adding a New Tool

1. Implement the function in `tools/session.py` or `tools/insights.py`
2. Import it in `server.py`
3. Register with `@mcp.tool()`:

```python
@mcp.tool()
def my_new_tool(param: Annotated[str, "description"]) -> str:
    result = my_function(param)
    return json.dumps(result)
```

1. Add the tool to `specs/SDD.md` Section 3 (Tool Reference)
2. Add a test in `tests/test_tools.py`
