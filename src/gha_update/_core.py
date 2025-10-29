from __future__ import annotations

import os
import re
import tomllib
import typing as t
from asyncio import Task
from asyncio import TaskGroup
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from pathlib import Path

from httpx import AsyncClient
from httpx import Response

Config = t.TypedDict(
    "Config",
    {
        "tag-only": list[str],
        "ghes-host": str | None,
    },
)
default_config: Config = {
    "tag-only": [],
    "ghes-host": None,
}


def load_config_path(path: os.PathLike[str] | str) -> Config:
    path = Path(path)

    if path.exists():
        data = tomllib.loads(path.read_text("utf-8"))
        config = data.get("tool", {}).get("gha-update", {})
    else:
        config = {}

    return {**default_config, **config}  # pyright: ignore


async def update_workflows(config: Config | None = None) -> None:
    if config is None:
        config = default_config

    if config["ghes-host"] is None:
        base_url = "https://api.github.com"
    else:
        base_url = f"https://{config['ghes-host']}/api/v3/"

    workflows = read_workflows()
    actions: set[str] = set()

    for path_actions in workflows.values():
        actions.update(path_actions)

    versions = await get_versions(base_url, actions)
    write_workflows(config, workflows, versions)


def iter_workflows() -> Iterator[Path]:
    cwd = Path.cwd()
    gh_path = cwd / ".github"
    workflows_path = gh_path / "workflows"
    actions_path = gh_path / "actions"

    if workflows_path.exists():
        for path in workflows_path.iterdir():
            if not (path.name.endswith(".yaml") or path.name.endswith(".yml")):
                continue

            yield path

    if actions_path.exists():
        for path in actions_path.iterdir():
            if (file := find_local_action(path)) is not None:
                yield file

    if (file := find_local_action(cwd)) is not None:
        yield file


def find_local_action(path: Path) -> Path | None:
    for ext in "yaml", "yml":
        if (file := path / f"action.{ext}").exists():
            return file

    return None


def read_workflows() -> dict[Path, set[str]]:
    out: dict[Path, set[str]] = {}

    for path in iter_workflows():
        out[path] = set()

        for line in path.read_text("utf-8").splitlines():
            if (name := find_name_in_line(line)) is None:
                continue

            out[path].add(name)

    return out


def find_name_in_line(line: str) -> str | None:
    uses = line.partition(" uses:")[2].strip("'\" \t\n\r\f\v")

    # ignore other lines, and local and docker actions
    if not uses or uses.startswith(("./")) or uses.startswith("docker://"):
        return None

    parts = uses.partition("@")[0].split("/")

    # repo must be owner/name
    if len(parts) < 2:
        return None

    # omit subdirectory
    return "/".join(parts[:2])


async def make_request(client: AsyncClient, url: str) -> Response:
    response = await client.get(url, follow_redirects=True)

    if response.status_code == 403:
        raise RuntimeError(
            "GitHub API rate limit reached. Authenticate by setting the"
            " GITHUB_TOKEN environment variable."
        )

    return response


next_link_re = re.compile(r'<([^>]+?)>; rel="next"', flags=re.ASCII)


async def get_highest_version(client: AsyncClient, name: str) -> tuple[str, str]:
    tags: dict[str, str] = {}
    url = f"/repos/{name}/tags"

    while True:
        response = await make_request(client, url)
        tags.update({t["name"]: t["commit"]["sha"] for t in response.json()})
        link_header = response.headers.get("link")

        if link_header is None or (m := next_link_re.search(link_header)) is None:
            break

        url = m.group(1)

    try:
        return highest_version(tags)
    except ValueError as e:
        raise RuntimeError(
            f"{name} has no version tags, it cannot be updated or pinned."
        ) from e


async def get_versions(
    base_url: str, names: Iterable[str]
) -> dict[str, tuple[str, str]]:
    tasks: dict[str, Task[tuple[str, str]]] = {}
    headers: dict[str, str] = {}

    if github_token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {github_token}"

    async with (
        AsyncClient(base_url=base_url, headers=headers) as c,
        TaskGroup() as tg,
    ):
        for name in names:
            tasks[name] = tg.create_task(get_highest_version(c, name))

    return {name: task.result() for name, task in tasks.items()}


def highest_version(tags: dict[str, str]) -> tuple[str, str]:
    versions: dict[tuple[int, ...], str] = {}

    for name in tags:
        try:
            parts = tuple(int(p) for p in name.removeprefix("v").split("."))
        except ValueError:
            continue

        versions[parts] = name

    if not versions:
        raise ValueError("no valid version tags found")

    version = versions[max(versions)]
    return version, tags[version]


def write_workflows(
    config: Config, paths: Iterable[Path], versions: Mapping[str, tuple[str, str]]
) -> None:
    for path in paths:
        out: list[str] = []

        for line in path.read_text("utf-8").splitlines():
            if (name := find_name_in_line(line)) is not None and name in versions:
                left, _, right = line.partition("@")
                tag, commit = versions[name]
                print(left)
                if match := re.search(r"uses:\s*(['\"])?", line):
                    maybe_quote = match.group(1) or ""
                else:
                    maybe_quote = ""
                if name in config["tag-only"]:
                    line = f"{left}@{tag}{maybe_quote}"
                else:
                    line = f"{left}@{commit}{maybe_quote} # {tag}"
                print(line)

            out.append(line)

        out.append("")
        path.write_text("\n".join(out), "utf-8")
