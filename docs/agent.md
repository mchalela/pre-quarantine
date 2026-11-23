# Working with a Claude Code helper

[← Back to the README](../README.md)

The agent's rules ship as templates in [`agent/`](../agent/). They only take effect once you activate them in this folder, so do that before the first session, and again after every `git pull`:

```bash
cd ~/Pre-Quarantine
tools/install-agent-rules.sh     # copies agent/CLAUDE.md and agent/settings.json into place
claude
```

Without that step an agent started here has no rules and no permission blocks. The other scripts print a warning when the active copies fall behind the templates.

Then: "inspect and convert everything in QUARANTINE/sender and tell me what it is". The agent can run inspect, convert and extract without asking. It cannot read originals, use the web, start subagents or use MCP tools, cannot edit the tools, keeps no memory between sessions, and has to ask for everything else. Say no to anything that looks odd. Use the terminal, not VS Code; if you do open this in VS Code, open this folder (never a subfolder of `QUARANTINE/`), pick Restricted Mode, and don't click files in `QUARANTINE/`.

Your own settings still count in this folder. A broad allow rule in `~/.claude/settings.json` (for example one that allows every shell command) also applies here and would let the agent run things without asking; the blocks above still win over it. Check that file before the first session.
