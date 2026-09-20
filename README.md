# docker-util

A small per-directory Docker workflow: `build` tags an image after the
current directory, `init`/`run` create and re-enter containers built from
it, and `fix`/`list`/`remove` manage what gets left behind.

This is a Python rewrite of an older bash script (`docker-util`). It has the
same commands and naming conventions, so anything scripted against the old
tool keeps working, but the implementation is now a tested Python package
instead of ~650 lines of bash.

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
git clone <this repo> ~/desktop/programs/projects/docker-util
cd ~/desktop/programs/projects/docker-util
uv tool install .
```

`uv tool install` puts a `docker-util` command on your `PATH` (in
`~/.local/bin` by default). To pick up local changes after editing the
source, run `uv tool install --reinstall .` again.

If you'd rather not install it globally, `uv run docker-util <command>` runs
it from inside the project directory without touching your `PATH`.

## Concepts

Every image and container name is derived from the directory you run
`docker-util` in:

- **image name**: `<your-username>-<directory-name, lowercased>`
- **container name**: `<image name>-<the name you give it>`

So running `docker-util build` in `~/projects/my-app` as user `sophie`
builds an image called `sophie-my-app`, and `docker-util init dev` creates a
container called `sophie-my-app-dev` from it. This is why every command
(except `init`/`run`, which take a container name) is run from inside the
project directory with no arguments.

## Commands

Run `docker-util --help` or `docker-util <command> --help` for the
authoritative, up-to-date usage of each command.

- **`build [--no-cache]`** — Builds the image for the current directory from
  its `Dockerfile`. `--no-cache` builds from scratch.
- **`init <name>`** — Creates a new container named `<name>` from the
  current directory's image, and configures it: sets up a shared,
  ACL-writable mount at `/mnt`, forwards a handful of environment variables,
  configures git, timezone, and SSH inside the container, installs Claude
  Code, and authorizes the GitHub CLI. See [Configuring `init`](#configuring-init)
  below — most of this is specific to one workflow and meant to be edited.
- **`run <name>`** — Starts an existing container and attaches an
  interactive shell to it.
- **`fix [name]`** — Repairs ownership of a mount directory that a
  container (running as root) wrote to. With no argument, repairs the
  shared `/mnt` mount; with a container name, repairs that container's own
  mount from before mounts were shared. Newer containers (created by
  `init`) shouldn't need this, since they get a standing ACL automatically.
- **`list` / `ls`** — Lists the current directory's image and any
  containers/volumes derived from it.
- **`remove [name]` / `rm [name]`** — With a container name, kills and
  removes that container. With no argument, removes the current directory's
  image (refusing if a container still depends on it).

### What changed from the bash version

- `test` and `copy` are gone. Both were already marked `deprecated` (an
  immediate `exit 1`) in the bash script; there was nothing left to port.
- `init`'s timezone step now uses the same constant it writes to the
  container's `TZ` environment variable, instead of reading the *host*
  shell's `$TZ` (which was usually unset, silently leaving `/etc/localtime`
  a broken symlink).
- Every optional setup step in `init` (git identity, vimrc, SSH keys, Claude
  Code, GitHub auth, ...) now reports a `warning: ... continuing.` line if
  it fails, instead of failing silently.

## Configuring `init`

`init` sets up a container for one specific workflow (Justin's), and that
setup is concentrated in [`src/docker_util/config.py`](src/docker_util/config.py)
so it's easy to adapt without reading through the command logic. Most
values can also be overridden with an environment variable at run time:

| Setting | Env var | Default |
| --- | --- | --- |
| Shared mount directory | `DOCKER_UTIL_MOUNT_DIR` | `~/mnt` |
| Container timezone | `DOCKER_UTIL_TZ` | `America/Chicago` |
| Container app directory | `DOCKER_UTIL_APP_DIR` | `/app/llm-serving` |
| Container working directory | `DOCKER_UTIL_WORKDIR` | `<app dir>/research` |
| git `user.email` in new containers | `DOCKER_UTIL_GIT_EMAIL` | `justin.m.garrigus@gmail.com` |
| git `user.name` in new containers | `DOCKER_UTIL_GIT_NAME` | `justinmgarrigus` |

`init` also forwards a fixed list of host environment variables into every
new container if they're set (notification/Telegram/Hugging
Face/Claude-Code tokens — see `FORWARDED_ENV_VARS` in `config.py`), and
best-effort copies in `~/.vimrc`, `~/.ssh`, and `~/.local/bin/notify-desktop`
if present. None of this runs for `build`, `run`, `fix`, `list`, or
`remove`.

`init` always creates containers with `--gpus all --runtime=nvidia`; there's
no CPU-only mode.

## Development

```
uv sync              # install dependencies, including dev tools
uv run pytest        # run the test suite
uv run ruff check .  # lint
uv run ruff format . # format
```

Tests mock every `docker`/`setfacl` call, so `uv run pytest` never touches a
real Docker daemon or your filesystem outside of `tmp_path`.
