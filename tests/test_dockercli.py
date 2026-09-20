"""Tests that `dockercli` builds the right `docker` command lines.

`subprocess.run` is mocked throughout: these tests never touch a real
Docker daemon.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from docker_util import dockercli


@pytest.fixture
def run(monkeypatch) -> MagicMock:
    mock = MagicMock(
        return_value=subprocess.CompletedProcess([], 0, stdout="", stderr="")
    )
    monkeypatch.setattr(dockercli.subprocess, "run", mock)
    return mock


def test_list_images_parses_and_drops_blank_lines(run: MagicMock) -> None:
    run.return_value = subprocess.CompletedProcess(
        [], 0, stdout="alpha\nbeta\n\n", stderr=""
    )
    assert dockercli.list_images() == ["alpha", "beta"]
    assert run.call_args.args[0] == [
        "docker",
        "image",
        "ls",
        "--format",
        "{{.Repository}}",
    ]


def test_image_exists_true_when_listed(run: MagicMock) -> None:
    run.return_value = subprocess.CompletedProcess(
        [], 0, stdout="sophie-app\n", stderr=""
    )
    assert dockercli.image_exists("sophie-app") is True
    assert dockercli.image_exists("someone-else") is False


def test_build_image_without_no_cache(run: MagicMock) -> None:
    dockercli.build_image("sophie-app", Path("/tmp/app"))
    assert run.call_args.args[0] == [
        "docker",
        "build",
        "-t",
        "sophie-app",
        "/tmp/app",
    ]


def test_build_image_with_no_cache(run: MagicMock) -> None:
    dockercli.build_image("sophie-app", Path("/tmp/app"), no_cache=True)
    assert run.call_args.args[0] == [
        "docker",
        "build",
        "-t",
        "sophie-app",
        "/tmp/app",
        "--no-cache",
    ]


def test_run_container_includes_mounts_env_and_gpus(run: MagicMock) -> None:
    dockercli.run_container(
        "sophie-app-dev",
        "sophie-app",
        mounts=[("/host/mnt", "/mnt")],
        env={"FOO": "bar"},
        gpus="all",
        runtime="nvidia",
        command=["/bin/bash"],
    )
    assert run.call_args.args[0] == [
        "docker",
        "run",
        "-d",
        "-i",
        "-t",
        "--name",
        "sophie-app-dev",
        "-v",
        "/host/mnt:/mnt",
        "-e",
        "FOO=bar",
        "--gpus",
        "all",
        "--runtime",
        "nvidia",
        "sophie-app",
        "/bin/bash",
    ]


def test_run_container_omits_gpus_and_runtime_when_not_given(
    run: MagicMock,
) -> None:
    dockercli.run_container("c", "img")
    assert run.call_args.args[0] == [
        "docker",
        "run",
        "-d",
        "-i",
        "-t",
        "--name",
        "c",
        "img",
    ]


def test_attach_shell_does_not_raise_on_nonzero_exit(run: MagicMock) -> None:
    dockercli.attach_shell("sophie-app-dev")
    assert run.call_args.kwargs["check"] is False


def test_copy_into_formats_container_colon_dest(run: MagicMock) -> None:
    dockercli.copy_into(
        "sophie-app-dev", Path("/home/sophie/.vimrc"), "/root/.vimrc"
    )
    assert run.call_args.args[0] == [
        "docker",
        "cp",
        "/home/sophie/.vimrc",
        "sophie-app-dev:/root/.vimrc",
    ]
