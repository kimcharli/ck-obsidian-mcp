# AGENTS

Agent operating guidelines for this repository.

## Source of truth

- Development docs are maintained only in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).
- Keep tool behavior and contracts aligned with [`specs/SDD.md`](specs/SDD.md).

## Session vs knowledge capture

- Use `log_message` for raw chronological conversation turns.
- Use `capture_insight` for durable knowledge:
  - best practices
  - lessons learned
  - reusable decisions
  - handoff-relevant context
- Do not treat session transcripts as the primary retrieval surface for reusable knowledge.

## Python workflow

- Use `uv` for Python commands in this project.
- Typical checks before finishing changes:
  - `uv run pre-commit run --all-files`
  - `uv run pytest -q`

## Safety and config

- Do not commit secrets (API keys, tokens).
- Keep secret values in local environment files.
- Prefer user-level MCP config for local secret-bearing settings.

## Editing scope

- Make minimal targeted changes.
- Avoid unrelated refactors.
- Keep docs and code synchronized when behavior changes.
