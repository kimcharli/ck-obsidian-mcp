"""Obsidian REST API client.

Wraps the Local REST API plugin (https://github.com/coddingtonbear/obsidian-local-rest-api).
All paths are vault-relative (e.g. "AI-Chats/Sessions/note.md").
"""
from __future__ import annotations

import httpx

from ck_obsidian_mcp.config import Settings


class ObsidianClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.obsidian_rest_api_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {settings.obsidian_rest_api_key}",
            "Content-Type": "text/markdown",
        }
        # The Local REST API plugin uses a self-signed cert for HTTPS
        self._verify = not self._base.startswith("https://localhost")

    def _client(self) -> httpx.Client:
        return httpx.Client(verify=self._verify)

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _vault_url(self, path: str) -> str:
        """Build URL for a vault-file endpoint."""
        clean = path.lstrip("/")
        return f"{self._base}/vault/{clean}"

    # ------------------------------------------------------------------
    # Note operations
    # ------------------------------------------------------------------

    def create_note(self, path: str, content: str) -> None:
        """Create (or overwrite) a note at *path* with *content*."""
        url = self._vault_url(path)
        with self._client() as client:
            resp = client.put(url, content=content.encode(), headers=self._headers)
            resp.raise_for_status()

    def get_note(self, path: str) -> str:
        """Return the raw Markdown content of a note."""
        url = self._vault_url(path)
        with self._client() as client:
            resp = client.get(
                url,
                headers={**self._headers, "Accept": "text/markdown"},
            )
            resp.raise_for_status()
            return resp.text

    def note_exists(self, path: str) -> bool:
        """Return True if the note exists in the vault."""
        url = self._vault_url(path)
        with self._client() as client:
            resp = client.get(
                url,
                headers={**self._headers, "Accept": "text/markdown"},
            )
            return resp.status_code == 200

    def append_to_note(self, path: str, content: str) -> None:
        """Append *content* to an existing note (creates it if absent)."""
        url = self._vault_url(path)
        with self._client() as client:
            # The REST API supports PATCH to append content
            resp = client.patch(
                url,
                content=content.encode(),
                headers=self._headers,
            )
            if resp.status_code == 404:
                # Note doesn't exist yet — create it
                self.create_note(path, content)
            else:
                resp.raise_for_status()

    def list_notes(self, folder: str) -> list[str]:
        """Return a list of file paths under *folder* in the vault."""
        url = f"{self._base}/vault/{folder.strip('/')}/"
        with self._client() as client:
            resp = client.get(url, headers={**self._headers, "Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()
            # Response shape: {"files": ["path/to/note.md", ...]}
            return data.get("files", [])
