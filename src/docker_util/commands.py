"""Implementations of the `docker-util` subcommands."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from . import acl, config, dockercli, githost, naming
from .errors import DockerUtilError


def cmd_build(*, directory: Path | None = None, no_cache: bool = False) -> None:
    """Builds an image tagged after `directory` (default: the cwd)."""
    directory = directory or Path.cwd()
    dockerfile = directory / "Dockerfile"
    if not dockerfile.is_file():
        raise DockerUtilError(f"no Dockerfile found in '{directory}'.")

    image = naming.image_name(directory)
    dockercli.build_image(image, directory, no_cache=no_cache)


def cmd_run(name: str, *, directory: Path | None = None) -> None:
    """Starts an existing container and attaches a shell to it."""
    directory = directory or Path.cwd()
    image = naming.image_name(directory)
    container = naming.container_name(image, name)

    if not dockercli.container_exists(container):
        raise DockerUtilError(
            f"a container named '{container}' does not exist."
        )

    dockercli.start_container(container)
    dockercli.attach_shell(container)


def cmd_fix(name: str | None = None, *, directory: Path | None = None) -> None:
    """Reclaims ownership of a root-owned mount directory."""
    directory = directory or Path.cwd()
    image = naming.image_name(directory)

    if name is None:
        mount_dir = config.MOUNT_DIR
        container = None
    else:
        container = naming.container_name(image, name)
        mount_dir = config.MOUNT_DIR / container

    if not mount_dir.is_dir():
        raise DockerUtilError(
            f"the mount directory '{mount_dir}' does not exist."
        )

    container_ok = container is not None and dockercli.container_exists(
        container
    )
    if not container_ok and not dockercli.image_exists(image):
        raise DockerUtilError(
            f"the image '{image}' does not exist, so there is no way to take "
            f"ownership of the root-owned files in '{mount_dir}'."
        )

    print(f'Taking ownership of "{mount_dir}" ... ', end="", flush=True)
    try:
        acl.mnt_reclaim(mount_dir, image, container)
    except subprocess.CalledProcessError as exc:
        print("failed")
        raise DockerUtilError(str(exc)) from exc
    acl.mnt_acl(mount_dir, recursive=True)
    print("done")


def cmd_list(*, directory: Path | None = None) -> None:
    """Prints the image, containers, and volumes tied to a directory."""
    directory = directory or Path.cwd()
    image = naming.image_name(directory)

    image_display = image if dockercli.image_exists(image) else "(none)"

    prefix = f"{image}-"
    containers = sorted(
        name[len(prefix) :]
        for name in dockercli.list_containers()
        if name.startswith(prefix)
    )
    volumes = sorted(
        name[len(prefix) :]
        for name in dockercli.list_volumes()
        if name.startswith(prefix)
    )

    print(f"Image: {image_display}")
    print(f"Containers: {', '.join(containers) or '(none)'}")
    print(f"Volumes: {', '.join(volumes) or '(none)'}")


def cmd_remove(
    name: str | None = None, *, directory: Path | None = None
) -> None:
    """Removes a directory's image, or one of its containers."""
    directory = directory or Path.cwd()
    image = naming.image_name(directory)

    if name is None:
        if not dockercli.image_exists(image):
            raise DockerUtilError(
                f"an image with the name '{image}' does not exist."
            )
        if image in dockercli.list_container_images():
            raise DockerUtilError(
                "at least one container depends on this image; remove those "
                "first."
            )
        dockercli.remove_image(image)
        return

    container = naming.container_name(image, name)
    if not dockercli.container_exists(container):
        raise DockerUtilError(f"the container '{container}' does not exist.")
    dockercli.kill_container(container)
    dockercli.remove_container(container)


def _claude_settings_patch_script(app_dir: str) -> str:
    """Builds a `python3 -c` script that trusts `app_dir` and wires up hooks."""
    hook_events = ("UserPromptSubmit", "Notification", "Stop")

    def _hook(event: str) -> list[dict]:
        command = f"{config.NOTIFY_HOOK_COMMAND} hook-{event.lower()}"
        return [{"hooks": [{"type": "command", "command": command}]}]

    hooks = {event: _hook(event) for event in hook_events}
    onboarding_patch = {
        "hasCompletedOnboarding": True,
        "projects": {app_dir: {"hasTrustDialogAccepted": True}},
    }
    settings = json.dumps({"hooks": hooks})
    return (
        "import json\n"
        "with open('/root/.claude.json') as f:\n"
        "    data = json.load(f)\n"
        f"data.update({onboarding_patch!r})\n"
        "with open('/root/.claude.json', 'w') as f:\n"
        "    json.dump(data, f)\n"
        "with open('/root/.claude/settings.json', 'w') as f:\n"
        f"    f.write({settings!r})\n"
    )


def _best_effort(description: str, action: Callable[[], None]) -> None:
    """Runs `action`, warning (not raising) if it fails.

    Mirrors the ground-truth bash script, where every post-creation setup
    step in `init` runs unconditionally regardless of earlier failures.
    """
    try:
        action()
    except (subprocess.CalledProcessError, OSError) as exc:
        print(
            f"\nwarning: {description} failed ({exc}); continuing.",
            file=sys.stderr,
        )


def cmd_init(name: str, *, directory: Path | None = None) -> None:
    """Creates and configures a new container from this directory's image."""
    directory = directory or Path.cwd()
    image = naming.image_name(directory)

    if not dockercli.image_exists(image):
        raise DockerUtilError(
            f"an image with the name '{image}' does not exist."
        )

    container = naming.container_name(image, name)
    if dockercli.container_exists(container):
        raise DockerUtilError(
            f"a container with the name '{container}' already exists."
        )

    # One mount directory, shared by every container, so a file is in the
    # same place no matter which container produced it. Deliberately never
    # cleared here: it holds every other container's output too.
    mount_dir = config.MOUNT_DIR
    figures_dir = mount_dir / "figures"
    research_dir = mount_dir / "research"
    with contextlib.suppress(PermissionError):
        figures_dir.mkdir(parents=True, exist_ok=True)
        research_dir.mkdir(parents=True, exist_ok=True)

    # A container created before the mount was shared can have left this
    # root-owned. Reclaim it now rather than failing confusingly later.
    if not os.access(figures_dir, os.W_OK) or not os.access(
        research_dir, os.W_OK
    ):
        acl.mnt_reclaim(mount_dir, image)
        figures_dir.mkdir(parents=True, exist_ok=True)
        research_dir.mkdir(parents=True, exist_ok=True)

    acl.mnt_acl(mount_dir)
    acl.mnt_acl(figures_dir)
    acl.mnt_acl(research_dir)

    app_dir = config.APP_DIR or naming.container_app_dir(directory)
    work_dir = config.WORKDIR or app_dir

    env = {var: os.environ.get(var, "") for var in config.FORWARDED_ENV_VARS}
    env["TZ"] = config.TIMEZONE
    env["DOCKER_CONTAINER_NAME"] = container
    env["DOCKER_PATH"] = work_dir
    env["FIGURES"] = "/mnt/figures"
    env["RESEARCH_PATH"] = "/mnt/research"

    print("Creating the container ... ", end="", flush=True)
    dockercli.run_container(
        container,
        image,
        mounts=[
            (str(mount_dir), "/mnt"),
            ("/var/run/docker.sock", "/var/run/docker.sock"),
        ],
        env=env,
        gpus="all",
        runtime="nvidia",
        command=["/bin/bash"],
        quiet=True,
    )
    print("done")

    print("Configuring the container ... ", end="", flush=True)

    git_email = config.GIT_USER_EMAIL or githost.config_value("user.email")
    git_name = config.GIT_USER_NAME or githost.config_value("user.name")

    def _set_git_identity() -> None:
        if git_email:
            dockercli.exec_container(
                container,
                ["git", "config", "--global", "user.email", git_email],
            )
        if git_name:
            dockercli.exec_container(
                container, ["git", "config", "--global", "user.name", git_name]
            )

    if git_email or git_name:
        _best_effort("setting git identity", _set_git_identity)
    _best_effort(
        "copying .vimrc",
        lambda: dockercli.copy_into(
            container, config.VIMRC_PATH, "/root/.vimrc"
        ),
    )
    _best_effort(
        "setting the timezone",
        lambda: (
            dockercli.exec_container(
                container,
                [
                    "ln",
                    "-snf",
                    f"/usr/share/zoneinfo/{config.TIMEZONE}",
                    "/etc/localtime",
                ],
            ),
            dockercli.exec_container(
                container,
                ["bash", "-c", f'echo "{config.TIMEZONE}" > /etc/timezone'],
            ),
        ),
    )
    _best_effort(
        "copying ssh keys",
        lambda: (
            dockercli.copy_into(container, config.SSH_DIR, "/root"),
            dockercli.exec_container(
                container, ["chown", "-R", "root:root", "/root/.ssh"]
            ),
        ),
    )
    _best_effort(
        "installing Claude Code",
        lambda: dockercli.exec_container(
            container,
            ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"],
        ),
    )
    _best_effort(
        "configuring Claude Code",
        lambda: dockercli.exec_container(
            container,
            ["python3", "-c", _claude_settings_patch_script(app_dir)],
        ),
    )
    _best_effort(
        "installing notification hook",
        lambda: dockercli.copy_into(
            container, config.NOTIFY_DESKTOP_PATH, "/bin/notify-desktop"
        ),
    )

    def _gh_auth() -> None:
        with config.GH_TOKEN_FILE.open() as token_file:
            dockercli.exec_container(
                container,
                [
                    "gh",
                    "auth",
                    "login",
                    "--hostname",
                    "github.com",
                    "--with-token",
                ],
                stdin=token_file,
            )
        dockercli.exec_container(
            container, ["gh", "config", "set", "git_protocol", "ssh"]
        )

    _best_effort("authorizing the GitHub CLI", _gh_auth)

    print("done")
