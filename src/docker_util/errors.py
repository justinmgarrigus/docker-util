"""Errors that are reported to the user without a traceback."""

from __future__ import annotations


class DockerUtilError(Exception):
    """Raised for expected failures (bad arguments, missing resources, ...)."""
