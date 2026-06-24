"""MCP configuration helpers for OpenCode (pilot: config file based)."""

from pathlib import Path


def default_opencode_config_path() -> Path:
    return Path("opencode.json")
