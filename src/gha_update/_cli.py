import asyncio
from pathlib import Path

import click

from ._core import load_config_path
from ._core import update_workflows


@click.command
@click.option(
    "config_path",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("pyproject.toml"),
    help="TOML file containing a [tool.gha-update] section.",
)
def cli(config_path: Path) -> None:
    """Update GitHub Actions to the latest versions, using the commit hash."""
    config = load_config_path(config_path)
    asyncio.run(update_workflows(config))
