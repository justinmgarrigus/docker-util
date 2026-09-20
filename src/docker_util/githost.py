"""Reads the invoking host's own git identity, as a fallback for `init`.

Kept separate from `commands.py` so tests can mock it without also mocking
every other subprocess call `init` makes.
"""

from __future__ import annotations

import subprocess


def config_value(key: str) -> str | None:
    """Returns `git config --global <key>` on the host, or None if unset."""
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None
