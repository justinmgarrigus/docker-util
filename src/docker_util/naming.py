"""Naming conventions shared by every command.

An image is named after the user and the directory it was built from; a
container is that image name plus a caller-chosen suffix. Keeping this in one
place means `build`, `init`, `run`, `fix`, `list`, and `remove` all agree on
what "this directory's image" is.
"""

from __future__ import annotations

import getpass
from pathlib import Path


def project_name(directory: Path) -> str:
    """Returns the lowercase directory name used as an image's suffix."""
    return directory.name.lower()


def image_name(directory: Path, user: str | None = None) -> str:
    """Returns the image name for `directory` (default: the current user)."""
    user = user or getpass.getuser()
    return f"{user}-{project_name(directory)}"


def container_name(image: str, name: str) -> str:
    """Returns the container name for `name` under `image`."""
    return f"{image}-{name}"
