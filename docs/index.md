# GitHub Actions Updater

Update GitHub Actions version pins in GitHub workflow files. Even with grouped,
monthly updates, Dependabot PRs can still be noisy, especially for smaller or
stable projects. This tool allows updating pins locally, when the maintainer
wants to.

## Install

Install from [PyPI] in a virtualenv using an installer such as [pip]. Or install
globally with an installer such as [pipx]:

[PyPI]: https://pypi.org/project/gha-update/
[pip]: https://pip.pypa.io
[pipx]: https://pipx.pypa.io

```
$ pip install gha-update
```

```
$ pipx install gha-update
```

## Source

The project is hosted on GitHub: <https://github.com/davidism/gha-update>.

## Running

Running the `gha-update` command will update all workflow files
(`.yaml`/`.yml`) in `.github/workflows` and subdirectories, and all action
files (`action.yaml`/`.yml`) in `.github/actions` subdirectories or the
project root. The highest tag for each action is found, and the commit hash for
that tag is used to update the pin. The version tag is added as a comment for
reference.

## Configuration

Configuration is taken from the `[tool.gha-update]` section of a project's
`pyproject.toml` file. The `--config` option can be used to select a different
TOML file. The following options are available:

-   `tag-only`: A list of action names to pin using the tag name only, rather
    than the commit hash for that tag. For example, the
    `slsa-framework/slsa-github-generator` action can't work correctly when
    pinned as a hash.
-   `ghes-host`: The hostname when using GitHub Enterprise Server.
-   `check-paths`: Any additional paths to check alongside the default `.github` folder.


Making requests to GitHub's API is rate limited, with a higher limit if an
access token is used. If the `GITHUB_TOKEN` environment variable is set, it will
be used to authenticate requests.

```{toctree}
:hidden:

tox
changes
license
```
