# Tox Environments

A convenient way to use this tool is with a [Tox] environment. Other
environments can be added for updating other pinned tools, such as [pre-commit]
hooks and [pip-tools] for Python requirements files. A label can be used to
create one command that runs all three update environments.

[Tox]: https://tox.wiki
[pre-commit]: https://pre-commit.com
[pip-tools]: https://pip-tools.readthedocs.io

```ini
[testenv:update-actions]
labels = update
commands = python -m gha_update

[testenv:update-pre_commit]
labels = update
deps = pre-commit
skip_install = true
commands = pre-commit autoupdate -j4

[testenv:update-requirements]
base_python = 3.12
labels = update
deps = pip-tools
skip_install = true
change_dir = requirements
commands =
    pip-compile build.in -q {posargs:-U}
    pip-compile docs.in -q {posargs:-U}
    pip-compile tests.in -q {posargs:-U}
    pip-compile typing.in -q {posargs:-U}
    pip-compile dev.in -q {posargs:-U}
```

You can run a single environment to update the corresponding pins:

```
$ tox r -e update-actions
```

Or all the environments labeled `update`:

```
$ tox r -m update
```
