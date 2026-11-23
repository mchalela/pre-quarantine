# Untrusted repos, step by step

[← Back to the README](../README.md)

```bash
cd ~/Pre-Quarantine
git clone --depth 1 --no-recurse-submodules https://github.com/them/repo.git QUARANTINE/sender/repo   # cloning does not run anything
tools/q-shell.sh QUARANTINE/sender/repo          # shell inside the container, NO network
```

That clone is the last git command to run on that folder from the host. Once code from the repo has run in the shell, the folder's git config may have been rewritten to run a program the next time git looks at it. To get a newer version, delete the folder and clone again.

Inside the shell, before running anything, read the files that execute code on your behalf:

- `package.json` (the `scripts` block, especially `preinstall` / `postinstall`), `setup.py`, `pyproject.toml`
- `.pre-commit-config.yaml`, `Makefile`, `conftest.py`, `.envrc`, `.vscode/tasks.json`, `.github/workflows/`
- then: `grep -rnE "base64|eval\(|exec\(|child_process|subprocess|curl |wget |atob\(" . | head -50`

Only if it reads clean and needs dependencies: exit and reopen with `tools/q-shell.sh QUARANTINE/sender/repo --net`.
Even then the code sees only that folder, never the home directory. But `--net` is more than the internet: the code can also reach services that listen on this machine and other devices on your local network. Docker cannot fence those off; the shell does get a network of its own, away from other containers. For Node work add `--image node:22-slim`.

While a shell is open on a folder, the other scripts refuse to touch files in it: code running there could swap a file under them. Close the shell first.

Hooks under `.git/hooks` are not installed by a clone. The real risk is `npm install`, `pip install -e .`, `pre-commit install`, `pytest` and `make`, which is why those only ever happen in the container.

For anything that needs a desktop app, a database or days of work: use a throwaway virtual machine (Gnome Boxes), snapshot it clean, revert afterwards.
