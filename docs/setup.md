# Setup on a new machine

[← Back to the README](../README.md)

Needs Linux and bash. Written on Ubuntu with GNOME; adapt the desktop steps elsewhere.

**1. Docker**

```bash
sudo apt install docker.io
sudo usermod -aG docker "$USER"     # then log out and back in
docker run --rm hello-world         # must work without sudo
```

Being in the docker group is equivalent to having root on the machine. That is the usual trade-off on a personal computer; don't do it on a shared one.

**2. The tools**

```bash
git clone https://github.com/mchalela/pre-quarantine.git ~/Pre-Quarantine && cd ~/Pre-Quarantine
chmod 700 .                      # keep other users out
tools/build.sh                   # builds the tools image (uses the network)
docker pull python:3.12-slim     # image used by tools/q-shell.sh, so the first run works offline
tools/demo-inspect.sh            # inert preview of what an inspection looks like
tools/install-agent-rules.sh     # only if you will use a Claude Code helper in this folder
```

```
Pre-Quarantine/
├── README.md      the routine and what to do with each kind of file
├── docs/          this page, untrusted repos, the helper agent, the MCP server, security model, development
├── agent/         rules and hard permission blocks for a helper agent (templates)
├── tools/         scripts that handle files inside a locked-down container
├── mcp-server/    optional: the same tools for an agent in another project
├── QUARANTINE/    ⛔ untrusted originals. NEVER double-click anything in here
└── CLEAN/         ✅ converted copies that are safe to open
```

**3. Your browser.** This is the first line of defence: a download must stay a download. The setting names differ per browser (look under Downloads, or Files and Applications), but the four goals are the same:

- [ ] **Ask where to save each file**, so it goes straight into `QUARANTINE/<sender>/` and never sits in Downloads.
- [ ] **PDFs are saved, not opened** in the browser's built-in viewer or an external one.
- [ ] **Nothing opens automatically after downloading.** Turn off any "always open files of this type" choice.
- [ ] **Links that launch desktop apps ask first.** Pages can trigger editors, chat and meeting apps through special links; set those handlers to "always ask".

**4. Desktop**

- [ ] Desktop search: nothing to do. The `.trackerignore` file in this folder makes the GNOME indexer skip it. Don't add this folder under Settings → Search → Search Locations.
- [ ] Thumbnails: the file manager previews files in any folder you open. Either never double-click inside `QUARANTINE/` and accept the sandboxed thumbnailer, or turn previews off: Files → menu → Preferences → Performance → Show Thumbnails → Never.
- [ ] Optional folder icons, so the danger zone is obvious: right-click a folder → Properties → click the icon → pick from `/usr/share/icons/Yaru/256x256/`.
  - `Pre-Quarantine`: `emblems/emblem-readonly.png` (padlock)
  - `QUARANTINE`: `status/dialog-error.png` (red no-entry sign)
  - `CLEAN`: `emblems/emblem-default.png` (green check mark)
  - `tools` and `.claude`: leave the default folder icon

**5. Git.** A repository's own config file can tell git to run programs, so git must never run inside `QUARANTINE/` on the host. Two habits cover it:

- [ ] Never run a git command in a folder under `QUARANTINE/`, and if your shell prompt shows git status, don't `cd` into those folders either: the prompt runs git for you. The scripts here take paths, so there is no need to.
- [ ] Optional but recommended: `git config --global safe.bareRepository explicit`. Without it, a folder that merely looks like a bare repository is enough for git to read its config.

`QUARANTINE/` and `CLEAN/` are ignored by git on purpose: never commit what strangers send you, or copies of it.
