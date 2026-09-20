from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

from docker_util import githost


def test_config_value_returns_the_stripped_value(monkeypatch) -> None:
    run = MagicMock(
        return_value=subprocess.CompletedProcess(
            [], 0, stdout="a@b.com\n", stderr=""
        )
    )
    monkeypatch.setattr(githost.subprocess, "run", run)

    assert githost.config_value("user.email") == "a@b.com"
    assert run.call_args.args[0] == ["git", "config", "--global", "user.email"]


def test_config_value_returns_none_when_unset(monkeypatch) -> None:
    def _raise(*_args: object, **_kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, ["git"])

    monkeypatch.setattr(githost.subprocess, "run", _raise)
    assert githost.config_value("user.email") is None


def test_config_value_returns_none_when_git_is_missing(monkeypatch) -> None:
    def _raise(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(githost.subprocess, "run", _raise)
    assert githost.config_value("user.email") is None
