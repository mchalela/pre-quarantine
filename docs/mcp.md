# The MCP server: the tools for an agent in another project

[← Back to the README](../README.md)

Optional. It adds nothing if you run the scripts by hand. It is for one situation: you are working with an AI agent in some other project and want it to check a file you saved into `QUARANTINE/`, without starting a session in this folder. The server offers the tools over MCP (the Model Context Protocol), so any client that speaks it can use them.

## Setup

Needs Python 3.10 or later on the host, next to Docker and a built tools image.

```bash
cd ~/Pre-Quarantine
python3 -m venv mcp-server/.venv
mcp-server/.venv/bin/pip install -r mcp-server/requirements.txt     # uses the network
```

Then tell your client how to start it: the Python of that environment, and the path of `server.py`. In Claude Code, for all your projects:

```bash
claude mcp add --scope user pre-quarantine -- ~/Pre-Quarantine/mcp-server/.venv/bin/python ~/Pre-Quarantine/mcp-server/server.py
```

Other clients take the same two values in their configuration file, usually in this shape, with full paths:

```json
{
  "mcpServers": {
    "pre-quarantine": {
      "command": "/home/you/Pre-Quarantine/mcp-server/.venv/bin/python",
      "args": ["/home/you/Pre-Quarantine/mcp-server/server.py"]
    }
  }
}
```

The server works on the install it sits in, and has no setting that could point it at another folder. After a `git pull`, run the `pip install` line again.

Then, from any project: "check `QUARANTINE/sender/brief.pdf` in my Pre-Quarantine and tell me what it is".

## What the agent can do, and what it cannot

| Tool | What it does |
|---|---|
| `list_files` | Names and sizes of the files in `QUARANTINE/`. Never contents. |
| `inspect` | Runs `tools/q-inspect.sh`. Returns the verdict (OK, CAUTION, STOP), the next step, and the report. |
| `convert` | Runs `tools/q-convert.sh`. Returns the folder in `CLEAN/`, the number of pages, and whether there is text. |
| `extract` | Runs `tools/q-extract.sh`. Returns the folder with the unpacked files, each still to be inspected. |
| `read_converted` | The text of a converted copy, 16,000 bytes at a time. |

There is no tool for the sandbox shell, none that deletes, and no option on any tool: the network cannot be turned on and the size limit of an extraction cannot be lifted. Those stay with you, by hand.

## How it is built

- **Every tool that touches an original runs the script.** The check that a path is inside `QUARANTINE/` stays in the scripts; the server passes the path on and reports the refusal.
- **Convert and extract inspect first.** They refuse on STOP, or when the inspection fails. An agent is told to inspect first; here it cannot skip it. By hand you still can.
- **The sender's words are kept apart.** In every result, what comes from the file sits under one field named `untrusted`: names, the type description, archive listings, findings, converted text. The verdict and the next step are outside it, read only from the lines the script writes itself.
- **What a file can push at the agent is bounded.** Reports are cut at 200 lines and text comes in pieces. Characters that cannot be seen (zero-width spaces, direction marks, Unicode tags) are left out of the text and counted: a person reading the copy would not notice them, a model would read them.
- **It talks over stdin and stdout only.** It opens no port, so nothing on the network can reach it.

## Fence the agent in

The server adds a safe way to reach a file. It does not take the unsafe ways away: an agent in another project still has its own tools, and the rules in [`agent/`](../agent/) only bind an agent started in this folder.

In Claude Code, read-only commands such as `cat` run without asking, on any path. So block the direct routes for every project, in `~/.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "Read(~/Pre-Quarantine/QUARANTINE/**)",
      "Edit(~/Pre-Quarantine/**)"
    ]
  }
}
```

These rules stop the file tools and the shell commands Claude Code recognises as reading a file. They do not stop a program the agent writes that opens the file itself. With another client, check what its agent can reach on your disk before relying on it.

For a batch of files, an agent started in this folder under the [helper-agent rules](agent.md) is fenced in more tightly than any agent working from elsewhere.

## Limits

- **An agent can still be talked into things.** Converted text enters its context, and so do names and listings in a report. Labelling them as the sender's words helps and does not solve it. Read what the agent proposes before you approve it.
- **Page pictures are not sent through the server.** An agent that can open files can view the PNGs in `CLEAN/`. One that cannot will not see a scan, and says so.
- **Leaving out invisible characters changes some texts**, for example in scripts that join letters with them. The copy in `CLEAN/` is left as it is.
- **It puts Python packages on the host, outside the container.** The MCP SDK is pinned to one version, but the packages it depends on are not. Keep them in the virtual environment above.
- **Everything in [Security model and limits](security.md) still applies.** The server is only as good as the scripts it runs.
