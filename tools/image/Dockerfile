# Tools for looking at untrusted files. Runs with no network, no home, read-only root.
FROM alpine:3.20
RUN apk add --no-cache file mupdf-tools libarchive-tools libreoffice \
    font-dejavu font-liberation coreutils
COPY q /usr/local/bin/q
RUN chmod 755 /usr/local/bin/q
ENV HOME=/tmp
ENTRYPOINT ["/usr/local/bin/q"]
