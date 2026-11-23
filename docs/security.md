# Security model and limits

[← Back to the README](../README.md)

## What the container does and does not protect

- **Does:** no network, no access to home, SSH keys, browser profiles or tokens; read-only system; no root capabilities; file arrives on stdin so it is never mounted; every run is stopped after 15 minutes.
- **The scripts do not take the container's word for anything.** A file that manages to take over a parser controls what the container prints and writes, so the host side checks it: output reaches the terminal as plain text only, the `verdict:` and `next:` lines are written on the host from a fixed set of words, only `page-NNN.png`, `text.txt` and `content.txt` are let into `CLEAN/` (with control characters stripped from the text), and an extracted folder is cleaned of links, pipes and exec bits by the host.
- **A file name cannot disguise itself on screen.** Names are shown in plain characters only, and an odd one appears in escaped form in the `next:` command, so what you paste is exactly that file.
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
