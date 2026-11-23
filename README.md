# 🔒 Pre-Quarantine

[![CI](https://github.com/mchalela/pre-quarantine/actions/workflows/ci.yml/badge.svg)](https://github.com/mchalela/pre-quarantine/actions/workflows/ci.yml)

A place to look at files from senders you don't know or can't verify yet, without getting hacked.
The rule behind everything here: **downloading and moving a file is safe; opening or running it is where the danger is.**

> A personal setup, shared as is. It lowers risk; it does not remove it, and it comes with no guarantee. Read the scripts before you trust them.

## What it looks like

Every file is first inspected inside a locked-down container. The report ends with a verdict and the command to run next:

```
$ tools/q-inspect.sh QUARANTINE/sender/document.pdf
file:    document.pdf
type:    PDF document, version 1.7
mime:    application/pdf
size:    245100 bytes
sha256:  07fd8c3817607d93da0000d04085a0bbbfff3462f659f6054c901615c75c03a1
Pages: 2
links:   1 (do not follow them)

  - PDF marker /JavaScript (2)
  - PDF marker /OpenAction (1)
  - PDF marker /EmbeddedFile (1)

verdict: CAUTION  suspicious content. Never open the original
next:    tools/q-convert.sh QUARANTINE/sender/document.pdf
```

`q-convert.sh` then turns the file into PNG pages and plain text in `CLEAN/`, which are safe to open. The original is never opened on your machine.

## Quick start

Needs Linux, bash and Docker.

```bash
git clone https://github.com/mchalela/pre-quarantine.git ~/Pre-Quarantine && cd ~/Pre-Quarantine
chmod 700 .                      # keep other users out
tools/build.sh                   # builds the tools image (uses the network)
docker pull python:3.12-slim     # image used by tools/q-shell.sh, so the first run works offline
tools/demo-inspect.sh            # inert preview of what an inspection looks like
```

Before the first real file, go through the [full setup](docs/setup.md): Docker itself, the browser settings that keep a download a download, the desktop and git.

## The routine

1. In the browser's save dialog, save straight into `QUARANTINE/<sender>/`. One subfolder per sender.
2. Open a terminal here: `cd ~/Pre-Quarantine`
3. Always start with: `tools/q-inspect.sh QUARANTINE/<sender>/<file>`
4. Read the last two lines. `verdict:` is 🟢 OK, 🟡 CAUTION or 🔴 STOP, and `next:` is the exact command to run. On STOP, delete the file. Whatever the verdict, never open the original: OK only means no known tricks were found.
5. Look at the result in `CLEAN/<sender>/`. Delete the original when you no longer need it. To convert a file again, delete its folder in `CLEAN/` first.

## What to do with each kind of file

| File | Do this | Never |
|---|---|---|
| PDF | `tools/q-convert.sh <file>` then open the PNGs in `CLEAN/<sender>/<name>/` | Double-click it |
| Office: .docx .xlsx .pptx .doc .xls .rtf .odt | `tools/q-convert.sh <file>` | Open in LibreOffice, enable macros |
| Macro files: .docm .xlsm .pptm | Same, and treat the sender with suspicion | |
| Archive: .zip .tar.gz .7z .rar | `tools/q-inspect.sh` to list, `tools/q-extract.sh` to unpack. Result stays in `QUARANTINE/`; treat each file inside by its own type | Extract with the file manager |
| Repo or code (.py .js .sh .ipynb, git URL) | Clone or extract into `QUARANTINE/`, read first, then `tools/q-shell.sh QUARANTINE/<dir>` ([step by step](docs/untrusted-repos.md)) | Run, install, use git on it, or open as a VS Code workspace on the host |
| Installer or binary: .deb .AppImage .exe .jar .run | Don't. Ask the sender why they are sending one | |
| Launcher: .desktop .lnk .url | Delete. Inspect only if curious | |
| SVG, HTML | `tools/q-inspect.sh`; read as text in the sandbox shell | Open in the browser |
| Image: .png .jpg .gif .webp | `tools/q-convert.sh` re-renders it | Open the original in a viewer or the browser |
| Text: .txt .csv .json .md | `tools/q-convert.sh` copies it to `CLEAN/<sender>/<name>/`; open in a text editor | Open a .csv in LibreOffice Calc |

If the extension and the `type:` line from `q-inspect` disagree, believe `q-inspect` and be suspicious.

## 🚩 Red flags that mean "walk away", whatever the file contains

- A request to clone and run a repo as a "quick test" before you have any established relationship with the sender.
- A call or meeting that requires installing their own app, a "codec", a font, or a browser extension.
- A document that needs "enable editing" or "enable content" to be read.
- Password-protected archives with the password in the message (it is there to get past scanners).
- Urgency plus a move to Telegram, WhatsApp or email.

## What it protects, and what it does not

- **The container** has no network and no access to home, SSH keys, browser profiles or tokens. Its system is read-only, it has no root capabilities, the file arrives on stdin so it is never mounted, and every run is stopped after 15 minutes.
- **The scripts do not take the container's word for anything.** They write the `verdict:` and `next:` lines themselves, let only plain text reach the terminal, and check every file before it lands in `CLEAN/`.
- **It does not** stop a kernel-level container escape (rare and expensive, not spent on ordinary targets), or stop *you* from believing what a document says. A clean conversion of a phishing PDF is still a phishing PDF.
- **The verdict is a set of simple checks, not a malware scanner.** A file can pass every check and still be hostile, which is why the step after OK is "convert", never "open".
- **For documents alone, [Dangerzone](https://dangerzone.rocks) is the more rigorous tool.** This repo covers the routine around it: finding out what a file really is, archives, untrusted repositories, and fencing in an AI helper.

The full list is in [Security model and limits](docs/security.md).

## How it is built

- Bash scripts and one Docker image. Nothing runs in the background, and the host needs nothing installed besides Docker.
- Every parser (`file`, mupdf, libarchive, LibreOffice) runs only inside the container. The host never opens an original.
- The container is treated as possibly taken over: what it prints is filtered and what it writes is checked on the host.
- Over 120 tests run the real scripts against files generated on the spot, check the container's isolation directly, and include a stand-in for a taken-over container. CI runs them with ShellCheck on every push.
- A Claude Code agent can do the routine for you, fenced in by permission rules that ship as templates.
- Optional: an MCP server offers inspect, convert and extract to an agent working in another project. It needs Python on the host.

## Upkeep

- Rebuild the image once a month for security updates: `tools/build.sh` (the only step that uses the network). It warns when the base image itself has stopped getting fixes.
- To update: `git pull && tools/build.sh`, then `tools/install-agent-rules.sh` if you use a helper agent here.
- Delete a sender's files when you are done with them: `rm -rf -- QUARANTINE/<sender> CLEAN/<sender>`. To empty both folders completely: `find QUARANTINE CLEAN -mindepth 1 ! -path QUARANTINE/.gitkeep ! -path CLEAN/.gitkeep -delete` (unlike `rm -rf QUARANTINE/*`, this also removes hidden files).
- If you think something did run on the host: disconnect, change passwords from another device (email first, then accounts that hold money), revoke GitHub and other tokens, rotate SSH keys.

## More

- [Setup in full](docs/setup.md): Docker, browser, desktop and git settings.
- [Untrusted repos, step by step](docs/untrusted-repos.md): cloning code and running it in the sandbox shell.
- [Working with a Claude Code helper](docs/agent.md): activating the agent rules, and what they block.
- [The MCP server](docs/mcp.md): the tools for an agent in another project, and how to fence it in.
- [Security model and limits](docs/security.md): what is and is not protected, in detail.
- [Development](docs/development.md): the tests, and how to work on the tools.
