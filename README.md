# 🔒 Pre-Quarantine

[![CI](https://github.com/mchalela/pre-quarantine/actions/workflows/ci.yml/badge.svg)](https://github.com/mchalela/pre-quarantine/actions/workflows/ci.yml)

A place to look at files from senders you don't know or can't verify yet, without getting hacked.
The rule behind everything here: **downloading and moving a file is safe; opening or running it is where the danger is.**

> A personal setup, shared as is. It lowers risk; it does not remove it, and it comes with no guarantee. Read the scripts before you trust them.

## Setup on a new machine

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

```
Pre-Quarantine/
├── README.md      this file
├── agent/         rules and hard permission blocks for a helper agent (templates)
├── tools/         scripts that handle files inside a locked-down container
├── QUARANTINE/    ⛔ untrusted originals. NEVER double-click anything in here
└── CLEAN/         ✅ converted copies that are safe to open
```

## The routine

1. In the browser's save dialog, save straight into `QUARANTINE/<sender>/`. One subfolder per sender.
2. Open a terminal here: `cd ~/Pre-Quarantine`
3. Always start with: `tools/q-inspect.sh QUARANTINE/<sender>/<file>`
4. Read the last two lines. `verdict:` is 🟢 OK, 🟡 CAUTION or 🔴 STOP, and `next:` is the exact command to run. Both lines are written by the script on your machine, never by the file, and an odd file name shows up there in escaped form. On STOP, delete the file. Whatever the verdict, never open the original: OK only means no known tricks were found.
5. Look at the result in `CLEAN/<sender>/`. Delete the original when you no longer need it. To convert a file a second time, delete its folder in `CLEAN/` first: the script never writes into a folder that is already there.

## What to do with each kind of file

| File | Do this | Never |
|---|---|---|
| PDF | `tools/q-convert.sh <file>` then open the PNGs in `CLEAN/<sender>/<name>/` | Double-click it |
| Office: .docx .xlsx .pptx .doc .xls .rtf .odt | `tools/q-convert.sh <file>` | Open in LibreOffice, enable macros |
| Macro files: .docm .xlsm .pptm | Same, and treat the sender with suspicion | |
| Archive: .zip .tar.gz .7z .rar | `tools/q-inspect.sh` to list, `tools/q-extract.sh` to unpack. Result stays in `QUARANTINE/`; treat each file inside by its own type | Extract with the file manager |
| Repo or code (.py .js .sh .ipynb, git URL) | Clone or extract into `QUARANTINE/`, read first, then `tools/q-shell.sh QUARANTINE/<dir>` | Run, install, use git on it, or open as a VS Code workspace on the host |
| Installer or binary: .deb .AppImage .exe .jar .run | Don't. Ask the sender why they are sending one | |
| Launcher: .desktop .lnk .url | Delete. Inspect only if curious | |
| SVG, HTML | `tools/q-inspect.sh`; read as text in the sandbox shell | Open in the browser |
| Image: .png .jpg .gif .webp | `tools/q-convert.sh` re-renders it | Open the original in a viewer or the browser |
| Text: .txt .csv .json .md | `tools/q-convert.sh` copies it to `CLEAN/<sender>/<name>/`; open in a text editor | Open a .csv in LibreOffice Calc |

If the extension and the `type:` line from `q-inspect` disagree, believe `q-inspect` and be suspicious.

## Untrusted repos, step by step

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

## Working with Claude here

The agent's rules ship as templates in `agent/`. They only take effect once you activate them in this folder, so do that before the first session, and again after every `git pull`:

```bash
cd ~/Pre-Quarantine
tools/install-agent-rules.sh     # copies agent/CLAUDE.md and agent/settings.json into place
claude
```

Without that step an agent started here has no rules and no permission blocks. The other scripts print a warning when the active copies fall behind the templates.

Then: "inspect and convert everything in QUARANTINE/sender and tell me what it is". The agent can run inspect, convert and extract without asking. It cannot read originals, use the web, start subagents or use MCP tools, cannot edit the tools, keeps no memory between sessions, and has to ask for everything else. Say no to anything that looks odd. Use the terminal, not VS Code; if you do open this in VS Code, open this folder (never a subfolder of `QUARANTINE/`), pick Restricted Mode, and don't click files in `QUARANTINE/`.

Your own settings still count in this folder. A broad allow rule in `~/.claude/settings.json` (for example one that allows every shell command) also applies here and would let the agent run things without asking; the blocks above still win over it. Check that file before the first session.

## What the container does and does not protect

- **Does:** no network, no access to home, SSH keys, browser profiles or tokens; read-only system; no root capabilities; file arrives on stdin so it is never mounted; every run is stopped after 15 minutes.
- **The scripts do not take the container's word for anything.** A file that manages to take over a parser controls what the container prints and writes, so the host side checks it: output reaches the terminal as plain text only, the `verdict:` and `next:` lines are written on the host from a fixed set of words, only `page-NNN.png`, `text.txt` and `content.txt` are let into `CLEAN/` (with control characters stripped from the text), and an extracted folder is cleaned of links, pipes and exec bits by the host.
- **Does not:** stop a kernel-level container escape (rare and expensive, not spent on ordinary targets), or stop *you* from believing what a document says. A clean conversion of a phishing PDF is still a phishing PDF: don't follow its links, don't move the conversation off the platform you met on, don't install what it tells you to.
- **Does not check the pixels.** A converter that was taken over could still write a PNG built to attack an image viewer. That takes a second, separate exploit; Dangerzone (see Limits) closes this gap, this repo does not.
- **The sandbox shell is looser on purpose:** the folder is writable, with `--net` the code reaches this machine's services and your local network as well as the internet, and it can see where the folder sits on your disk (the path includes your user name).
- `text.txt` in `CLEAN/` is safe to open but is still the stranger's words.

## Limits

- **The verdict is a set of simple checks, not a malware scanner.** It looks at the real file type, the name, archive listings, and well-known active-content markers in PDF and Office files. A file can pass every check and still be hostile, which is why the next step after OK is still "convert", never "open".
- **Legacy Office formats (.doc, .xls, .ppt) are checked only by a text search for macro markers.** Treat them with more suspicion than the newer formats.
- **The Office checks cover macro projects, embedded objects and content loaded from outside the file.** Other carriers exist, such as formula fields that start programs and macro sheets in old `.xls` files, and are not detected. The conversion runs none of them.
- **Archives are listed and extracted inside the container, but onto your disk.** `q-extract.sh` refuses an archive that unpacks to more than 2 GB or 100,000 entries; add `--big` after the path if you expected one that large. Inside an archive only the file names are checked, so inspect each extracted file on its own.
- **Long documents are cut:** a conversion stops after 500 pages and a text copy after 5 MB. The script says so when it happens.
- **Linux only**, and it relies on Docker's isolation. Anyone who can use Docker on a machine is effectively an administrator of it.
- **For documents alone, [Dangerzone](https://dangerzone.rocks) is the more rigorous tool**: it does the same pixel conversion with stronger isolation and a maintained team behind it. This repo covers the rest of the routine around it: finding out what a file really is, archives, untrusted repositories, and fencing in an AI helper.

## Development

Develop in a separate clone, not in the folder you use for real files: an editor with extensions should never be open on a folder that holds untrusted files.

```bash
git clone https://github.com/mchalela/pre-quarantine.git ~/Projects/pre-quarantine-dev && cd ~/Projects/pre-quarantine-dev
pip install -r tests/requirements.txt
pytest
```

The tests build their own image (`quarantine-tools-test`) from the checkout, so they never replace the image your working install uses.

Do not run `tools/install-agent-rules.sh` in a development clone: the agent rules are meant to stop an agent from editing the tools, which is exactly what development needs. If you ran it by mistake, `tools/install-agent-rules.sh --remove` undoes it.

The tests run the real scripts against files generated on the spot (no hostile samples are stored in the repo), and check the container's isolation directly: no network, no capabilities, read-only system, no view of the home directory. CI runs the same tests plus ShellCheck on every push.

## Upkeep

- Rebuild the image once a month for security updates: `tools/build.sh` (the only step that uses the network). It builds from scratch each time so the newest packages are fetched, and it warns when the base image itself has stopped getting fixes and `tools/image/Dockerfile` needs a newer one.
- To update: `git pull && tools/build.sh`, then `tools/install-agent-rules.sh` if you use a helper agent here.
- Delete a sender's files when you are done with them. Converted copies keep the sender's subfolder, so from this folder, in a terminal: `rm -rf -- QUARANTINE/<sender> CLEAN/<sender>`. To empty both folders completely: `find QUARANTINE CLEAN -mindepth 1 ! -path QUARANTINE/.gitkeep ! -path CLEAN/.gitkeep -delete` (unlike `rm -rf QUARANTINE/*`, this also removes hidden files, and it spares only the two placeholder files, not anything a sender named the same).
- This folder has a `.trackerignore` file so desktop search skips it. Don't browse `QUARANTINE/` in the file manager, or turn thumbnails off: Files → menu → Preferences → Performance → Show Thumbnails → Never.
- If you think something did run on the host: disconnect, change passwords from another device (email first, then accounts that hold money), revoke GitHub and other tokens, rotate SSH keys.

## 🚩 Red flags that mean "walk away", whatever the file contains

- A request to clone and run a repo as a "quick test" before you have any established relationship with the sender.
- A call or meeting that requires installing their own app, a "codec", a font, or a browser extension.
- A document that needs "enable editing" or "enable content" to be read.
- Password-protected archives with the password in the message (it is there to get past scanners).
- Urgency plus a move to Telegram, WhatsApp or email.
