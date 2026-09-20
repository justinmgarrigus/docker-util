from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from docker_util import cli
from docker_util.errors import DockerUtilError


@pytest.mark.parametrize(
    ("argv", "func_name", "call_args"),
    [
        (["build"], "cmd_build", {"no_cache": False}),
        (["build", "--no-cache"], "cmd_build", {"no_cache": True}),
        (["init", "dev"], "cmd_init", ("dev",)),
        (["run", "dev"], "cmd_run", ("dev",)),
        (["fix"], "cmd_fix", (None,)),
        (["fix", "dev"], "cmd_fix", ("dev",)),
        (["list"], "cmd_list", ()),
        (["ls"], "cmd_list", ()),
        (["remove"], "cmd_remove", (None,)),
        (["remove", "dev"], "cmd_remove", ("dev",)),
        (["rm", "dev"], "cmd_remove", ("dev",)),
    ],
)
def test_dispatches_to_the_matching_command(
    monkeypatch, argv, func_name, call_args
) -> None:
    mock = MagicMock()
    monkeypatch.setattr(cli.commands, func_name, mock)

    assert cli.main(argv) == 0

    if isinstance(call_args, dict):
        mock.assert_called_once_with(**call_args)
    else:
        mock.assert_called_once_with(*call_args)


def test_reports_a_docker_util_error_without_a_traceback(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        cli.commands, "cmd_list", MagicMock(side_effect=DockerUtilError("nope"))
    )

    assert cli.main(["list"]) == 1
    assert "Error: nope" in capsys.readouterr().err


def test_reports_a_failed_docker_command(monkeypatch, capsys) -> None:
    error = subprocess.CalledProcessError(1, ["docker", "build"])
    monkeypatch.setattr(cli.commands, "cmd_build", MagicMock(side_effect=error))

    assert cli.main(["build"]) == 1
    assert "docker build" in capsys.readouterr().err


def test_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        cli.main([])
