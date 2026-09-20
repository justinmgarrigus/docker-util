"""Defaults for `docker-util init`.

Everything here is specific to Justin's workflow rather than to Docker in
general, so it's collected in one place: edit this file (or the matching
environment variable) rather than hunting through `commands.py` when moving
to a new machine or project.

Nothing here affects `build`, `run`, `fix`, `list`, or `remove`.
"""

from __future__ import annotations

import os
from pathlib import Path

# Directory shared by every container on the host, bind-mounted at /mnt.
MOUNT_DIR = Path(
    os.environ.get("DOCKER_UTIL_MOUNT_DIR", str(Path.home() / "mnt"))
)

# Timezone configured inside every new container.
TIMEZONE = os.environ.get("DOCKER_UTIL_TZ", "America/Chicago")

# Working directory set inside every new container (its "app" checkout).
CONTAINER_APP_DIR = os.environ.get("DOCKER_UTIL_APP_DIR", "/app/llm-serving")
CONTAINER_WORKDIR = os.environ.get(
    "DOCKER_UTIL_WORKDIR", f"{CONTAINER_APP_DIR}/research"
)

# Host environment variables forwarded into every new container, when set.
FORWARDED_ENV_VARS = (
    "NOTIFY_BOT_TOKEN",
    "NOTIFY_CHAT_ID",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_BOT_TOKEN",
    "HF_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "NOTIFY_NTFY_BASE",
    "NOTIFY_NTFY_TOPIC",
)

GIT_USER_EMAIL = os.environ.get(
    "DOCKER_UTIL_GIT_EMAIL", "justin.m.garrigus@gmail.com"
)
GIT_USER_NAME = os.environ.get("DOCKER_UTIL_GIT_NAME", "justinmgarrigus")

VIMRC_PATH = Path.home() / ".vimrc"
SSH_DIR = Path.home() / ".ssh"
GH_TOKEN_FILE = Path.home() / ".ssh" / "gh_docker_token"
NOTIFY_DESKTOP_PATH = Path.home() / ".local" / "bin" / "notify-desktop"

NOTIFY_HOOK_COMMAND = "/bin/notify-desktop"
