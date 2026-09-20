from pathlib import Path

from docker_util import naming


def test_project_name_lowercases_the_directory_name() -> None:
    assert naming.project_name(Path("/home/sophie/Projects/My-App")) == "my-app"


def test_image_name_combines_user_and_project() -> None:
    directory = Path("/home/sophie/projects/docker-util")
    assert naming.image_name(directory, user="sophie") == "sophie-docker-util"


def test_image_name_defaults_to_the_current_user(monkeypatch) -> None:
    monkeypatch.setattr(naming.getpass, "getuser", lambda: "someone")
    directory = Path("/tmp/widget")
    assert naming.image_name(directory) == "someone-widget"


def test_container_name_appends_to_the_image_name() -> None:
    assert (
        naming.container_name("sophie-docker-util", "dev")
        == "sophie-docker-util-dev"
    )


def test_container_app_dir_preserves_case_unlike_the_image_name() -> None:
    assert naming.container_app_dir(
        Path("/home/sophie/projects/llm-serving")
    ) == ("/app/llm-serving")
    assert naming.container_app_dir(Path("/home/sophie/projects/MyApp")) == (
        "/app/MyApp"
    )
