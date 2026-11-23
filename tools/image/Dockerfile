# Tools for looking at untrusted files. Runs with no network, no home, read-only root.
# The parsers in here are the attack surface, so the base must be an Alpine branch that still gets
# security fixes (https://alpinelinux.org/releases/). tools/build.sh warns once this one runs out.
FROM alpine:3.24
RUN apk upgrade --no-cache && \
    apk add --no-cache file mupdf-tools libarchive-tools libreoffice \
    font-dejavu font-liberation coreutils
COPY q /usr/local/bin/q
RUN chmod 755 /usr/local/bin/q
ENV HOME=/tmp
# What q prints is read by the scripts on the host. Raise this number, here and in tools/_lib.sh,
# whenever that changes, so that an image built before a git pull is refused instead of misread.
LABEL pre-quarantine.protocol="2"
# A file built to keep a parser busy for ever is stopped after 15 minutes: timeout is process 1,
# so when it gives up the whole container goes with it.
ENTRYPOINT ["timeout", "-s", "KILL", "900", "/usr/local/bin/q"]
