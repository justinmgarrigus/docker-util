"""Thin wrappers around the `docker` CLI.

Nothing here knows about docker-util's naming conventions or workflow; it
just runs `docker` and parses its output. Keeping it separate is what lets
the rest of the package be tested by mocking a handful of functions instead
of a real Docker daemon.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(
    args: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    stdin: int | None = None,
) -> subprocess.CompletedProcess:
    """Runs `docker <args>`, optionally capturing (and hiding) its output."""
    stdout = subprocess.PIPE if capture else None
    stderr = subprocess.PIPE if capture else None
    return subprocess.run(
        ["docker", *args],
        check=check,
        stdout=stdout,
        stderr=stderr,
        stdin=stdin,
        text=True,
    )


def _names(args: list[str]) -> list[str]:
    result = _run(args, capture=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def list_images() -> list[str]:
    """Returns every image's repository name."""
    return _names(["image", "ls", "--format", "{{.Repository}}"])


def list_containers() -> list[str]:
    """Returns every container's name, running or not."""
    return _names(["container", "ls", "-a", "--format", "{{.Names}}"])


def list_container_images() -> list[str]:
    """Returns the image name backing each container, running or not."""
    return _names(["container", "ls", "-a", "--format", "{{.Image}}"])


def list_volumes() -> list[str]:
    """Returns every volume's name."""
    return _names(["volume", "ls", "--format", "{{.Name}}"])


def image_exists(name: str) -> bool:
    """True if an image named `name` exists."""
    return name in list_images()


def container_exists(name: str) -> bool:
    """True if a container named `name` exists."""
    return name in list_containers()


def build_image(image: str, context: Path, *, no_cache: bool = False) -> None:
    """Builds `context` (a directory with a Dockerfile) and tags it `image`."""
    args = ["build", "-t", image, str(context)]
    if no_cache:
        args.append("--no-cache")
    _run(args)


def run_container(
    container: str,
    image: str,
    *,
    mounts: list[tuple[str, str]] = (),
    env: dict[str, str] | None = None,
    gpus: str | None = None,
    runtime: str | None = None,
    command: list[str] | None = None,
    quiet: bool = False,
) -> None:
    """Creates and starts a detached, interactive container from `image`."""
    args = ["run", "-d", "-i", "-t", "--name", container]
    for src, dst in mounts:
        args += ["-v", f"{src}:{dst}"]
    for key, value in (env or {}).items():
        args += ["-e", f"{key}={value}"]
    if gpus is not None:
        args += ["--gpus", gpus]
    if runtime is not None:
        args += ["--runtime", runtime]
    args.append(image)
    if command:
        args += command
    _run(args, capture=quiet)


def run_throwaway(
    image: str, *, mounts: list[tuple[str, str]], command: list[str]
) -> None:
    """Runs `command` in a one-off, auto-removed container from `image`."""
    args = ["run", "--rm"]
    for src, dst in mounts:
        args += ["-v", f"{src}:{dst}"]
    args += [image, *command]
    _run(args, capture=True)


def start_container(container: str) -> None:
    """Starts an already-created container."""
    _run(["container", "start", container], capture=True)


def attach_shell(container: str) -> None:
    """Attaches an interactive `/bin/bash` shell to a running container."""
    _run(["exec", "-it", container, "/bin/bash"], check=False)


def exec_container(
    container: str, command: list[str], *, stdin: int | None = None
) -> None:
    """Runs `command` inside `container`, hiding its output."""
    _run(["exec", "-i", container, *command], capture=True, stdin=stdin)


def copy_into(container: str, src: Path, dest: str) -> None:
    """Copies a local file or directory into `container` at `dest`."""
    _run(["cp", str(src), f"{container}:{dest}"], capture=True)


def kill_container(container: str) -> None:
    """Kills a running container."""
    _run(["container", "kill", container], capture=True)


def remove_container(container: str) -> None:
    """Removes a (stopped) container."""
    _run(["container", "rm", container], capture=True)


def remove_image(image: str) -> None:
    """Removes an image."""
    _run(["image", "rm", image], capture=True)
