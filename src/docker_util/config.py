"""Defaults for `docker-util init`, all overridable by environment variable.

Nothing here is specific to one user or one project: identity comes from
the environment (falling back to the host's own `git config`), and the
in-container project path is derived from the directory `init` is run in
unless overridden. Nothing here affects `build`, `run`, `fix`, `list`, or
`remove`.
"""

from __future__ import annotations

import os
from pathlib import Path

# Directory shared by every container on the host, bind-mounted at /mnt.
MOUNT_DIR = Path(
    os.environ.get("DOCKER_UTIL_MOUNT_DIR", str(Path.home() / "mnt"))
)

# Timezone configured inside every new container.
TIMEZONE = os.environ.get("DOCKER_UTIL_TZ", "UTC")

# In-container project directory and working directory. Leaving these unset
# means "derive from the directory `init` is run in" (see
# naming.container_app_dir) and "same as the app directory", respectively.
# Set them when a project's Dockerfile uses a different convention -- e.g.
# llm-serving's Dockerfile does most of its work from a `research`
# subdirectory of its app directory.
APP_DIR = os.environ.get("DOCKER_UTIL_APP_DIR")
WORKDIR = os.environ.get("DOCKER_UTIL_WORKDIR")

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

# git identity configured inside every new container. Leaving these unset
# means "use the host's own `git config --global`", so this works with no
# configuration at all on a machine that already has git set up.
GIT_USER_EMAIL = os.environ.get("DOCKER_UTIL_GIT_EMAIL")
GIT_USER_NAME = os.environ.get("DOCKER_UTIL_GIT_NAME")

VIMRC_PATH = Path.home() / ".vimrc"
SSH_DIR = Path.home() / ".ssh"
GH_TOKEN_FILE = Path.home() / ".ssh" / "gh_docker_token"
NOTIFY_DESKTOP_PATH = Path.home() / ".local" / "bin" / "notify-desktop"

NOTIFY_HOOK_COMMAND = "/bin/notify-desktop"
