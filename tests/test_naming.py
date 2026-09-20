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


def test_image_name_sanitizes_an_email_style_username() -> None:
    directory = Path("/home/jmg22237/projects/docker-util")
    assert (
        naming.image_name(directory, user="jmg22237@austin.utexas.edu")
        == "jmg22237-austin.utexas.edu-docker-util"
    )


def test_image_name_sanitizes_an_unusual_directory_name() -> None:
    directory = Path("/home/sophie/projects/My Cool App!!")
    assert naming.image_name(directory, user="sophie") == "sophie-my-cool-app"


def test_sanitize_falls_back_when_nothing_valid_remains() -> None:
    directory = Path("/home/sophie/projects/@@@")
    assert naming.image_name(directory, user="@@@") == "user-project"


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
