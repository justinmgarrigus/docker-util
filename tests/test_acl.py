from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from docker_util import acl


def test_mnt_acl_warns_and_skips_when_setfacl_is_missing(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(acl.shutil, "which", lambda _: None)
    run = MagicMock()
    monkeypatch.setattr(acl.subprocess, "run", run)

    acl.mnt_acl(Path("/home/sophie/mnt"))

    run.assert_not_called()
    assert "setfacl is not available" in capsys.readouterr().out


def test_mnt_acl_grants_access_and_default_acl(monkeypatch) -> None:
    monkeypatch.setattr(acl.shutil, "which", lambda _: "/usr/bin/setfacl")
    monkeypatch.setattr(acl.os, "getuid", lambda: 1000)
    run = MagicMock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(acl.subprocess, "run", run)

    acl.mnt_acl(Path("/home/sophie/mnt"), recursive=True)

    access_call, default_call = run.call_args_list
    assert access_call.args[0] == [
        "setfacl",
        "-R",
        "-m",
        "u:1000:rwx",
        "-m",
        "m::rwx",
        "/home/sophie/mnt",
    ]
    assert default_call.args[0] == [
        "setfacl",
        "-R",
        "-d",
        "-m",
        "u:1000:rwx",
        "-m",
        "m::rwx",
        "/home/sophie/mnt",
    ]


def test_mnt_reclaim_uses_the_existing_container_when_present(
    monkeypatch,
) -> None:
    monkeypatch.setattr(acl.dockercli, "container_exists", lambda _: True)
    start = MagicMock()
    exec_ = MagicMock()
    throwaway = MagicMock()
    monkeypatch.setattr(acl.dockercli, "start_container", start)
    monkeypatch.setattr(acl.dockercli, "exec_container", exec_)
    monkeypatch.setattr(acl.dockercli, "run_throwaway", throwaway)
    monkeypatch.setattr(acl.os, "getuid", lambda: 1000)
    monkeypatch.setattr(acl.os, "getgid", lambda: 1000)

    acl.mnt_reclaim(Path("/home/sophie/mnt"), "sophie-app", "sophie-app-dev")

    start.assert_called_once_with("sophie-app-dev")
    assert exec_.call_count == 2
    throwaway.assert_not_called()


def test_mnt_reclaim_falls_back_to_a_throwaway_container(monkeypatch) -> None:
    monkeypatch.setattr(acl.dockercli, "container_exists", lambda _: False)
    throwaway = MagicMock()
    monkeypatch.setattr(acl.dockercli, "run_throwaway", throwaway)
    monkeypatch.setattr(acl.os, "getuid", lambda: 1000)
    monkeypatch.setattr(acl.os, "getgid", lambda: 1000)

    acl.mnt_reclaim(Path("/home/sophie/mnt"), "sophie-app", None)

    throwaway.assert_called_once()
    _, kwargs = throwaway.call_args
    assert kwargs["mounts"] == [("/home/sophie/mnt", "/mnt")]
    assert "chown -R 1000:1000 /mnt" in kwargs["command"][-1]
