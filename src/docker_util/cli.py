"""Command-line entry point for `docker-util`."""

from __future__ import annotations

import argparse
import subprocess
import sys

from . import commands
from .errors import DockerUtilError


def build_parser() -> argparse.ArgumentParser:
    """Builds the `docker-util` argument parser."""
    parser = argparse.ArgumentParser(
        prog="docker-util",
        description=(
            "Per-directory Docker workflow: `build` tags an image after the "
            "current directory, `init`/`run` create and re-enter containers "
            "from it, and `fix`/`list`/`remove` manage what's left behind."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        help="Build an image from the Dockerfile in the current directory.",
    )
    build.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without using the Docker layer cache.",
    )

    init = subparsers.add_parser(
        "init",
        help="Create and configure a container from this directory's image.",
    )
    init.add_argument(
        "name", help="Name to append to the image name for the new container."
    )

    run = subparsers.add_parser(
        "run", help="Start an existing container and attach a shell."
    )
    run.add_argument("name", help="Name of the container to run.")

    fix = subparsers.add_parser(
        "fix", help="Reclaim ownership of a root-owned mount directory."
    )
    fix.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Container whose own mount to repair; omit for the shared mount.",
    )

    subparsers.add_parser(
        "list",
        aliases=["ls"],
        help="List the image, containers, and volumes for this directory.",
    )

    remove = subparsers.add_parser(
        "remove",
        aliases=["rm"],
        help="Remove this directory's image, or a single container.",
    )
    remove.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Container to remove; omit to remove the image.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parses arguments and dispatches to the matching command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            commands.cmd_build(no_cache=args.no_cache)
        elif args.command == "init":
            commands.cmd_init(args.name)
        elif args.command == "run":
            commands.cmd_run(args.name)
        elif args.command == "fix":
            commands.cmd_fix(args.name)
        elif args.command in ("list", "ls"):
            commands.cmd_list()
        elif args.command in ("remove", "rm"):
            commands.cmd_remove(args.name)
    except DockerUtilError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        command = " ".join(exc.cmd)
        print(
            f"Error: `{command}` failed (exit {exc.returncode}).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
