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
        "check-paths": list[str]
    },
)
default_config: Config = {
    "tag-only": [],
    "ghes-host": None,
    "check-paths": []
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

    workflows = read_workflows(config["check-paths"])
    actions: set[str] = set()

    for path_actions in workflows.values():
        actions.update(path_actions)

    versions = await get_versions(base_url, actions)
    write_workflows(config, workflows, versions)


def iter_workflows(paths_to_check: list[str]) -> Iterator[Path]:
    cwd = Path.cwd()
    gh_path = cwd / ".github"
    workflows_path = gh_path / "workflows"
    actions_path = gh_path / "actions"
    extra_paths = [cwd / path_to_check for path_to_check in paths_to_check]

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

    for extra_path in extra_paths:
        if extra_path.exists():
            if extra_path.is_dir():
                # Find local actions at the root of specified path
                if (file := find_local_action(extra_path)) is not None:
                    yield file

                # Find local actions within the folders of specified path
                for path in extra_path.iterdir():
                    if (file := find_local_action(path)) is not None:
                        yield file

            else:
                if not (extra_path.name.endswith(".yaml") or extra_path.name.endswith(".yml")):
                    continue
                else:
                    yield extra_path


def find_local_action(path: Path) -> Path | None:
    for ext in "yaml", "yml":
        if (file := path / f"action.{ext}").exists():
            return file

    return None


def read_workflows(paths_to_check: list[str]) -> dict[Path, set[str]]:
    out: dict[Path, set[str]] = {}

    for path in iter_workflows(paths_to_check):
        out[path] = set()

        for line in path.read_text("utf-8").splitlines():
            if (name := find_name_in_line(line)) is None:
                continue

            out[path].add(name)

    return out


def find_name_in_line(line: str) -> str | None:
    uses = line.partition(" uses:")[2].strip()

    # ignore other lines, and local and docker actions
    if not uses or uses.startswith("./") or uses.startswith("docker://"):
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
    except ValueError:
        return await get_default_branch_commit(client, name)


async def get_default_branch_commit(client: AsyncClient, name: str) -> tuple[str, str]:
    response = await make_request(client, f"/repos/{name}")
    data = response.json()
    branch = data["default_branch"]
    response = await make_request(client, f"/repos/{name}/commits/{branch}")
    sha = response.json()["sha"]
    return branch, sha


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

                if name in config["tag-only"]:
                    line = f"{left}@{tag}"
                else:
                    line = f"{left}@{commit} # {tag}"

            out.append(line)

        out.append("")
        path.write_text("\n".join(out), "utf-8")
