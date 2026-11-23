# Development

[← Back to the README](../README.md)

Develop in a separate clone, not in the folder you use for real files: an editor with extensions should never be open on a folder that holds untrusted files.

```bash
git clone https://github.com/mchalela/pre-quarantine.git ~/Projects/pre-quarantine-dev && cd ~/Projects/pre-quarantine-dev
pip install -r tests/requirements.txt
pytest
```

The tests build their own images from the checkout (`quarantine-tools-test`, and a second one that plays a container taken over by a hostile file), so they never replace the image your working install uses. `tools/build.sh` does replace it: in a development clone, run it as `Q_IMAGE=some-other-name tools/build.sh`.

Do not run `tools/install-agent-rules.sh` in a development clone: the agent rules are meant to stop an agent from editing the tools, which is exactly what development needs. If you ran it by mistake, `tools/install-agent-rules.sh --remove` undoes it.

The tests run the real scripts against files generated on the spot (no hostile samples are stored in the repo), and check the container's isolation directly: no network, no capabilities, read-only system, no view of the home directory. CI runs the same tests plus ShellCheck on every push.

The scripts on the host read what `tools/image/q` prints. When that changes, raise the protocol number in both `tools/image/Dockerfile` and `tools/_lib.sh`, so that an image built before a `git pull` is refused instead of misread.

`mcp-server/server.py` in turn reads what the host scripts print: the verdict and next lines of `q-inspect.sh`, and the last lines of `q-convert.sh` and `q-extract.sh`. Change the two sides together. Its tests fail when only one moved, and they run the server from a copy inside a temporary install, so it never serves your real folders. `pip install -r tests/requirements.txt` also installs the MCP SDK those tests need.

The tests also put the eval harness in `evals/` through its self-test, with scripted agents in place of a model. A real run of the evals calls a model, costs money and is never part of the tests or of CI.
