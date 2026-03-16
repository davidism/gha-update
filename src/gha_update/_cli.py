import asyncio
from pathlib import Path

import click

from ._core import load_config_path
from ._core import update_workflows


@click.command
@click.option(
    "config_path",
    "--config",
    type=click.Path(exists=False, dir_okay=False, path_type=Path),
    default=Path("pyproject.toml"),
    help="TOML file containing a [tool.gha-update] section.",
)
@click.argument(
    "files", nargs=-1, type=click.Path(exists=False, dir_okay=False, path_type=Path)
)
def cli(config_path: Path, files: tuple[Path, ...]) -> None:
    """Update GitHub Actions to the latest versions, using the commit hash."""
    config = load_config_path(config_path)
    asyncio.run(update_workflows(config, files))
