"""Tests for the subcommand implementations.

`dockercli` and `acl` are mocked throughout: these tests never touch a real
Docker daemon or the filesystem outside of `tmp_path`.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from docker_util import commands
from docker_util.errors import DockerUtilError


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "my-app"
    directory.mkdir()
    return directory


# --- build -------------------------------------------------------------


def test_build_requires_a_dockerfile(project_dir: Path) -> None:
    with pytest.raises(DockerUtilError, match="Dockerfile"):
        commands.cmd_build(directory=project_dir)


def test_build_tags_the_image_after_the_directory(
    monkeypatch, project_dir: Path
) -> None:
    (project_dir / "Dockerfile").write_text("FROM scratch\n")
    build_image = MagicMock()
    monkeypatch.setattr(commands.dockercli, "build_image", build_image)
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")

    commands.cmd_build(directory=project_dir)

    build_image.assert_called_once_with(
        "sophie-my-app", project_dir, no_cache=False
    )


# --- run -----------------------------------------------------------------


def test_run_requires_an_existing_container(
    monkeypatch, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.dockercli, "container_exists", lambda _: False)
    with pytest.raises(DockerUtilError, match="does not exist"):
        commands.cmd_run("dev", directory=project_dir)


def test_run_starts_and_attaches(monkeypatch, project_dir: Path) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "container_exists", lambda _: True)
    start = MagicMock()
    attach = MagicMock()
    monkeypatch.setattr(commands.dockercli, "start_container", start)
    monkeypatch.setattr(commands.dockercli, "attach_shell", attach)

    commands.cmd_run("dev", directory=project_dir)

    start.assert_called_once_with("sophie-my-app-dev")
    attach.assert_called_once_with("sophie-my-app-dev")


# --- fix -------------------------------------------------------------------


def test_fix_requires_the_mount_directory_to_exist(
    monkeypatch, tmp_path: Path, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.config, "MOUNT_DIR", tmp_path / "missing")
    with pytest.raises(DockerUtilError, match="does not exist"):
        commands.cmd_fix(None, directory=project_dir)


def test_fix_requires_a_container_or_image(
    monkeypatch, tmp_path: Path, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.config, "MOUNT_DIR", tmp_path)
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: False)
    with pytest.raises(DockerUtilError, match="no way to take ownership"):
        commands.cmd_fix(None, directory=project_dir)


def test_fix_reclaims_the_shared_mount(
    monkeypatch, tmp_path: Path, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.config, "MOUNT_DIR", tmp_path)
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: True)
    reclaim = MagicMock()
    mnt_acl = MagicMock()
    monkeypatch.setattr(commands.acl, "mnt_reclaim", reclaim)
    monkeypatch.setattr(commands.acl, "mnt_acl", mnt_acl)

    commands.cmd_fix(None, directory=project_dir)

    reclaim.assert_called_once_with(tmp_path, "sophie-my-app", None)
    mnt_acl.assert_called_once_with(tmp_path, recursive=True)


def test_fix_reclaims_a_containers_own_mount(
    monkeypatch, tmp_path: Path, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.config, "MOUNT_DIR", tmp_path)
    container_dir = tmp_path / "sophie-my-app-dev"
    container_dir.mkdir()
    monkeypatch.setattr(commands.dockercli, "container_exists", lambda _: True)
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: True)
    reclaim = MagicMock()
    monkeypatch.setattr(commands.acl, "mnt_reclaim", reclaim)
    monkeypatch.setattr(commands.acl, "mnt_acl", MagicMock())

    commands.cmd_fix("dev", directory=project_dir)

    reclaim.assert_called_once_with(
        container_dir, "sophie-my-app", "sophie-my-app-dev"
    )


# --- list --------------------------------------------------------------


def test_list_reports_none_for_missing_resources(
    monkeypatch, capsys, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: False)
    monkeypatch.setattr(commands.dockercli, "list_containers", list)
    monkeypatch.setattr(commands.dockercli, "list_volumes", list)

    commands.cmd_list(directory=project_dir)

    out = capsys.readouterr().out
    assert "Image: (none)" in out
    assert "Containers: (none)" in out
    assert "Volumes: (none)" in out


def test_list_filters_and_strips_the_image_prefix(
    monkeypatch, capsys, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: True)
    monkeypatch.setattr(
        commands.dockercli,
        "list_containers",
        lambda: [
            "sophie-my-app-dev",
            "sophie-my-app-test",
            "sophie-other-thing",
        ],
    )
    monkeypatch.setattr(
        commands.dockercli, "list_volumes", lambda: ["sophie-my-app-dev"]
    )

    commands.cmd_list(directory=project_dir)

    out = capsys.readouterr().out
    assert "Image: sophie-my-app" in out
    assert "Containers: dev, test" in out
    assert "Volumes: dev" in out


# --- remove ------------------------------------------------------------


def test_remove_image_requires_it_to_exist(
    monkeypatch, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: False)
    with pytest.raises(DockerUtilError, match="does not exist"):
        commands.cmd_remove(None, directory=project_dir)


def test_remove_image_blocked_by_dependent_containers(
    monkeypatch, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: True)
    monkeypatch.setattr(
        commands.dockercli, "list_container_images", lambda: ["sophie-my-app"]
    )
    with pytest.raises(DockerUtilError, match="depends on this image"):
        commands.cmd_remove(None, directory=project_dir)


def test_remove_image_succeeds(monkeypatch, project_dir: Path) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: True)
    monkeypatch.setattr(commands.dockercli, "list_container_images", list)
    remove_image = MagicMock()
    monkeypatch.setattr(commands.dockercli, "remove_image", remove_image)

    commands.cmd_remove(None, directory=project_dir)

    remove_image.assert_called_once_with("sophie-my-app")


def test_remove_container_requires_it_to_exist(
    monkeypatch, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "container_exists", lambda _: False)
    with pytest.raises(DockerUtilError, match="does not exist"):
        commands.cmd_remove("dev", directory=project_dir)


def test_remove_container_kills_and_removes_it(
    monkeypatch, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "container_exists", lambda _: True)
    kill = MagicMock()
    remove = MagicMock()
    monkeypatch.setattr(commands.dockercli, "kill_container", kill)
    monkeypatch.setattr(commands.dockercli, "remove_container", remove)

    commands.cmd_remove("dev", directory=project_dir)

    kill.assert_called_once_with("sophie-my-app-dev")
    remove.assert_called_once_with("sophie-my-app-dev")


# --- init --------------------------------------------------------------


def test_init_requires_the_image_to_exist(
    monkeypatch, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: False)
    with pytest.raises(DockerUtilError, match="does not exist"):
        commands.cmd_init("dev", directory=project_dir)


def test_init_rejects_a_duplicate_container(
    monkeypatch, project_dir: Path
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: True)
    monkeypatch.setattr(commands.dockercli, "container_exists", lambda _: True)
    with pytest.raises(DockerUtilError, match="already exists"):
        commands.cmd_init("dev", directory=project_dir)


def test_init_creates_the_container_and_keeps_going_after_optional_failures(
    monkeypatch, tmp_path: Path, project_dir: Path, capsys
) -> None:
    monkeypatch.setattr(commands.naming.getpass, "getuser", lambda: "sophie")
    monkeypatch.setattr(commands.dockercli, "image_exists", lambda _: True)
    monkeypatch.setattr(commands.dockercli, "container_exists", lambda _: False)
    monkeypatch.setattr(commands.config, "MOUNT_DIR", tmp_path / "mnt")
    monkeypatch.setattr(commands.acl, "mnt_acl", MagicMock())
    monkeypatch.setattr(commands.acl, "mnt_reclaim", MagicMock())
    run_container = MagicMock()
    monkeypatch.setattr(commands.dockercli, "run_container", run_container)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("no such file")

    monkeypatch.setattr(commands.dockercli, "exec_container", _boom)
    monkeypatch.setattr(commands.dockercli, "copy_into", _boom)

    # No real ~/.ssh, ~/.vimrc, gh token, etc. on the test host -- every
    # optional step should fail, be reported, and not raise.
    commands.cmd_init("dev", directory=project_dir)

    run_container.assert_called_once()
    args, kwargs = run_container.call_args
    assert args[0] == "sophie-my-app-dev"
    assert args[1] == "sophie-my-app"
    assert kwargs["env"]["DOCKER_CONTAINER_NAME"] == "sophie-my-app-dev"
    assert kwargs["gpus"] == "all"

    out = capsys.readouterr()
    assert "warning:" in out.err
    assert (tmp_path / "mnt" / "figures").is_dir()


def test_claude_settings_patch_script_is_valid_python() -> None:
    script = commands._claude_settings_patch_script("/app/my-app")
    ast.parse(script)
    assert "/app/my-app" in script
