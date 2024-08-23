# GitHub Actions Updater

Update GitHub Actions version pins in GitHub workflow files. Even with grouped,
monthly updates, Dependabot PRs can still be noisy, especially for smaller or
stable projects. This tool allows updating pins locally, when the maintainer
wants to.

## Installing

Install from PyPI in a virtualenv using an installer such as [pip]. Or install
globally with an installer such as [pipx]:

[pip]: https://pip.pypa.io
[pipx]: https://pipx.pypa.io

```
$ pip install gha-update
```

```
$ pipx install gha-update
```

## Running

Running the `gha-update` command will update all workflow files
(`.yaml` or `.yml`) in `.github/workflows` and subdirectories. The highest
tag for each action is found, and the commit hash for that tag is used to update
the pin. The version tag is added as a comment for reference.

## Configuration

Configuration is taken from the `[tool.gha-update]` section of a project's
`pyproject.toml` file. The `--config` option can be used to select a different
TOML file. The following options are available:

-   `tag-only`: A list of action names to pin using the tag name only, rather
    than the commit hash for that tag. For example, the
    `slsa-framework/slsa-github-generator` action can't work correctly when
    pinned as a hash.

```{toctree}
:hidden:

tox
changes
license
```
