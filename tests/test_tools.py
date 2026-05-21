"""Tests for ck-obsidian-mcp tools using pytest-httpx to mock the Obsidian REST API."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_httpx import HTTPXMock

from ck_obsidian_mcp.config import InsightCategory, Settings
from ck_obsidian_mcp.obsidian.client import ObsidianClient


@pytest.fixture
def mock_settings(tmp_path) -> Settings:
    return Settings(
        obsidian_rest_api_url="http://localhost:27123",
        obsidian_rest_api_key="test-key",
        vault_root="AI-Chats",
    )


@pytest.fixture
def client(mock_settings) -> ObsidianClient:
    return ObsidianClient(mock_settings)


# ---------------------------------------------------------------------------
# ObsidianClient tests
# ---------------------------------------------------------------------------


class TestObsidianClient:
    def test_create_note(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="PUT",
            url="http://localhost:27123/vault/AI-Chats%2FSessions%2Ftest.md",
            status_code=200,
        )
        client.create_note("AI-Chats/Sessions/test.md", "# Hello")

    def test_append_to_note(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="PATCH",
            url="http://localhost:27123/vault/AI-Chats%2FSessions%2Ftest.md",
            status_code=200,
        )
        client.append_to_note("AI-Chats/Sessions/test.md", "\n## New section\n")

    def test_append_creates_when_not_found(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="PATCH",
            url="http://localhost:27123/vault/AI-Chats%2FSessions%2Fnew.md",
            status_code=404,
        )
        httpx_mock.add_response(
            method="PUT",
            url="http://localhost:27123/vault/AI-Chats%2FSessions%2Fnew.md",
            status_code=200,
        )
        client.append_to_note("AI-Chats/Sessions/new.md", "content")

    def test_list_notes(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="GET",
            url="http://localhost:27123/vault/AI-Chats%2FSessions/",
            json={"files": ["AI-Chats/Sessions/claude-2026-05-20-abc12345.md"]},
        )
        files = client.list_notes("AI-Chats/Sessions")
        assert len(files) == 1
        assert "claude" in files[0]


# ---------------------------------------------------------------------------
# Session tool tests
# ---------------------------------------------------------------------------


class TestSessionTools:
    def test_start_session(self, mock_settings, httpx_mock: HTTPXMock):
        # PUT to create the session note
        httpx_mock.add_response(method="PUT", status_code=200)
        # GET to fetch the last handoff (returns 404 = no prior handoff)
        httpx_mock.add_response(method="GET", status_code=404)

        with (
            patch("ck_obsidian_mcp.tools.session.settings", mock_settings),
            patch("ck_obsidian_mcp.tools.session._client", ObsidianClient(mock_settings)),
        ):
            from ck_obsidian_mcp.tools.session import start_session

            result = start_session(agent="claude", project="my-project", topic="Testing MCP")

        assert "session_id" in result
        assert result["agent"] == "claude"
        assert "note_path" in result

    def test_list_sessions_filters_by_agent(self, mock_settings, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            method="GET",
            json={
                "files": [
                    "AI-Chats/Sessions/claude-2026-05-20-abc.md",
                    "AI-Chats/Sessions/copilot-2026-05-20-def.md",
                ]
            },
        )
        with (
            patch("ck_obsidian_mcp.tools.session.settings", mock_settings),
            patch("ck_obsidian_mcp.tools.session._client", ObsidianClient(mock_settings)),
        ):
            from ck_obsidian_mcp.tools.session import list_sessions

            result = list_sessions(agent="claude")

        assert result["count"] == 1
        assert "claude" in result["sessions"][0]["agent"]


# ---------------------------------------------------------------------------
# Insight tool tests
# ---------------------------------------------------------------------------


class TestInsightTools:
    def test_capture_insight_creates_index(self, mock_settings, httpx_mock: HTTPXMock):
        # note_exists → 404, create index → 200, append → 200
        httpx_mock.add_response(method="GET", status_code=404)
        httpx_mock.add_response(method="PUT", status_code=200)
        httpx_mock.add_response(method="PATCH", status_code=200)

        with (
            patch("ck_obsidian_mcp.tools.insights.settings", mock_settings),
            patch("ck_obsidian_mcp.tools.insights._client", ObsidianClient(mock_settings)),
        ):
            from ck_obsidian_mcp.tools.insights import capture_insight

            result = capture_insight(
                session_id="abc12345",
                agent="claude",
                category=InsightCategory.decision,
                title="Use JWT for auth",
                content="Decided to use JWT because session tokens were flagged by legal.",
                tags=["auth", "security"],
            )

        assert result["ok"] is True
        assert result["category"] == "decision"
