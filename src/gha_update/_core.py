from __future__ import annotations

import os
import tomllib
import typing as t
from asyncio import Task
from asyncio import TaskGroup
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from httpx import Response

Config = t.TypedDict(
    "Config",
    {
        "tag-only": list[str],
    },
)
default_config: Config = {
    "tag-only": [],
}


def load_config_path(path: os.PathLike[str] | str) -> Config:
    data = tomllib.loads(Path(path).read_text("utf-8"))
    config = data.get("tool", {}).get("gha-update", {})
    return {**default_config, **config}


async def update_workflows(config: Config | None = None) -> None:
    if config is None:
        config = default_config

    workflows = read_workflows()
    actions: set[str] = set()

    for path_actions in workflows.values():
        actions.update(path_actions)

    versions = await get_versions(actions)
    write_workflows(config, workflows, versions)


def iter_workflows() -> Iterator[Path]:
    for path in (Path.cwd() / ".github" / "workflows").iterdir():
        if not (path.name.endswith(".yaml") or path.name.endswith(".yml")):
            continue

        yield path


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


async def get_versions(names: Iterable[str]) -> dict[str, tuple[str, str]]:
    tasks: dict[str, Task[Response]] = {}

    async with AsyncClient(base_url="https://api.github.com") as c, TaskGroup() as tg:
        for name in names:
            tasks[name] = tg.create_task(c.get(f"/repos/{name}/tags"))

    out: dict[str, tuple[str, str]] = {}

    for name, task in tasks.items():
        out[name] = highest_version(task.result().json())

    return out


def highest_version(tags: Iterable[Mapping[str, Any]]) -> tuple[str, str]:
    items: dict[str, str] = {t["name"]: t["commit"]["sha"] for t in tags}
    versions: dict[tuple[int, ...], str] = {}

    for name in items:
        try:
            parts = tuple(int(p) for p in name.removeprefix("v").split("."))
        except ValueError:
            continue

        versions[parts] = name

    version = versions[max(versions)]
    return version, items[version]


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
