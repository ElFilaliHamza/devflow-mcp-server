"""Read-only scanning of a project directory for onboarding metadata."""

from __future__ import annotations

from pathlib import Path

README_CANDIDATES = ("README.md", "README.rst", "README.txt", "README")
ENV_CANDIDATES = (".env.example", ".env.sample", ".env.template")


def _first_existing(path: Path, candidates: tuple[str, ...]) -> Path | None:
    for name in candidates:
        p = path / name
        if p.is_file():
            return p
    return None


def scan_readme(project_path: Path) -> str:
    """Return the contents of the project's README, or "" if none exists."""
    p = _first_existing(Path(project_path), README_CANDIDATES)
    if p is None:
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def scan_env_template(project_path: Path) -> str:
    """Return the contents of `.env.example` (or similar), or "" if missing."""
    p = _first_existing(Path(project_path), ENV_CANDIDATES)
    if p is None:
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def summarize_readme(text: str, max_chars: int = 800) -> str:
    """Return a short summary suitable for embedding in a resource.

    Truncates on a word boundary when possible, appending an ellipsis.
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    truncated = text[: max_chars - 1]
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"
