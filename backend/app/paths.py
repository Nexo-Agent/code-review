from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_OPENCODE_GENERATED_CONFIG = _REPO_ROOT / "opencode.generated.json"
DOCKER_OPENCODE_GENERATED_CONFIG = Path("/config/opencode.generated.json")


def opencode_generated_config_path() -> Path:
    """Fixed OpenCode config output path (Compose bind-mount or repo root)."""
    if DOCKER_OPENCODE_GENERATED_CONFIG.parent.is_dir():
        return DOCKER_OPENCODE_GENERATED_CONFIG
    return HOST_OPENCODE_GENERATED_CONFIG
