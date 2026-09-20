"""Naming conventions shared by every command.

An image is named after the user and the directory it was built from; a
container is that image name plus a caller-chosen suffix. Keeping this in one
place means `build`, `init`, `run`, `fix`, `list`, and `remove` all agree on
what "this directory's image" is.
"""

from __future__ import annotations

import getpass
import re
from pathlib import Path

# Docker image/container names are lowercase and built from runs of
# [a-z0-9] separated by single '.', '_', '__', or one-or-more '-'. Anything
# else (an email-style username's '@', say) gets collapsed to a single '-'.
_INVALID_DOCKER_CHARS = re.compile(r"[^a-z0-9._-]+")


def _sanitize(component: str, *, fallback: str) -> str:
    """Lowercases `component` into a valid Docker name component."""
    sanitized = _INVALID_DOCKER_CHARS.sub("-", component.lower()).strip("-._")
    return sanitized or fallback


def project_name(directory: Path) -> str:
    """Returns the Docker-safe directory name used as an image's suffix."""
    return _sanitize(directory.name, fallback="project")


def image_name(directory: Path, user: str | None = None) -> str:
    """Returns the image name for `directory` (default: the current user)."""
    user = user or getpass.getuser()
    return f"{_sanitize(user, fallback='user')}-{project_name(directory)}"


def container_name(image: str, name: str) -> str:
    """Returns the container name for `name` under `image`."""
    return f"{image}-{name}"


def container_app_dir(directory: Path) -> str:
    """Returns the in-container path a Dockerfile is expected to use.

    This is `/app/<directory name>`, case-preserved (unlike the image name,
    which is lowercased) so it matches what a Dockerfile's `WORKDIR`/
    `COPY . .` actually wrote.
    """
    return f"/app/{directory.name}"
