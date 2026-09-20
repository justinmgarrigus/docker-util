"""Ownership repair for mount directories written to by containers.

Containers run as root, so anything they write under a bind mount lands
root-owned on the host. `mnt_acl` grants the invoking user a standing ACL
on a directory (a *default* ACL makes it inherited by everything created
underneath, regardless of who created it) so this only has to be granted
once. `mnt_reclaim` is the one-time fix for a directory that predates that
ACL, or that was written to by a container that didn't set one.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import dockercli


def mnt_acl(path: Path, *, recursive: bool = False) -> None:
    """Grants the current user rwx on `path`, including future contents."""
    if shutil.which("setfacl") is None:
        print(
            f"Warning: setfacl is not available; files written into "
            f"'{path}' by the container will stay root-owned."
        )
        return

    uid = os.getuid()
    recurse_flag = ["-R"] if recursive else []
    subprocess.run(
        [
            "setfacl",
            *recurse_flag,
            "-m",
            f"u:{uid}:rwx",
            "-m",
            "m::rwx",
            str(path),
        ],
        check=True,
    )
    subprocess.run(
        [
            "setfacl",
            *recurse_flag,
            "-d",
            "-m",
            f"u:{uid}:rwx",
            "-m",
            "m::rwx",
            str(path),
        ],
        check=True,
    )


def mnt_reclaim(
    mount_dir: Path, image: str, container: str | None = None
) -> None:
    """Chowns `mount_dir` back to the current user via a root-run container.

    Uses `container` if it still exists, and otherwise a throwaway container
    from `image`, so this still works after the container itself was removed
    and only its mount directory is left behind.
    """
    uid, gid = os.getuid(), os.getgid()
    if container is not None and dockercli.container_exists(container):
        dockercli.start_container(container)
        dockercli.exec_container(
            container, ["chown", "-R", f"{uid}:{gid}", "/mnt"]
        )
        dockercli.exec_container(
            container, ["chmod", "-R", "u+rwX,go+rX", "/mnt"]
        )
    else:
        dockercli.run_throwaway(
            image,
            mounts=[(str(mount_dir), "/mnt")],
            command=[
                "bash",
                "-c",
                f"chown -R {uid}:{gid} /mnt && chmod -R u+rwX,go+rX /mnt",
            ],
        )
