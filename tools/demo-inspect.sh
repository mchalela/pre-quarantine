#!/usr/bin/env bash
# Inert preview of what tools/q-inspect.sh prints in each case.
# Touches no files and runs no container: every value below is made up.
# Same colours and layout as tools/q-inspect.sh, so edit here to try a design, then port it.
#   tools/demo-inspect.sh            all cases
#   tools/demo-inspect.sh stop       only cases whose title matches "stop"
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] || [ -n "${FORCE_COLOR:-}" ]; then
  R=$'\033[1;31m'; G=$'\033[1;32m'; Y=$'\033[1;33m'; C=$'\033[36m'; B=$'\033[1m'; D=$'\033[2m'; N=$'\033[0m'
else R=; G=; Y=; C=; B=; D=; N=; fi
filter="${1:-}"; show=1

title()   { if [[ -z "$filter" || "${1,,}" == *"${filter,,}"* ]]; then show=1; printf '\n%s━━━ %s ━━━%s\n' "$D" "$1" "$N"; else show=0; fi; }
row()     { [ $show = 1 ] && printf '%s%-8s%s %s\n' "$B" "$1" "$N" "$2"; }
head5()   { row "file:" "$1"; row "type:" "$2"; row "mime:" "$3"; row "size:" "$4 bytes"; row "sha256:" "$D$5$N"; }
plain()   { [ $show = 1 ] && printf '%s\n' "$1"; }
listing() { [ $show = 1 ] && printf '  %s%s%s\n' "$D" "$1" "$N"; }
blank()   { [ $show = 1 ] && echo; }
finding() { [ $show = 1 ] && printf '%s  - %s%s\n' "$Y" "$1" "$N"; }
verdict() { # OK|CAUTION|STOP  next-command
  [ $show = 1 ] || return 0
  case "$1" in
    OK)      col=$G; msg="no known tricks found. Still, never open the original" ;;
    CAUTION) col=$Y; msg="suspicious content. Never open the original" ;;
    STOP)    col=$R; msg="dangerous file. Delete it and be wary of the sender" ;;
  esac
  printf '%sverdict:%s %s%s%s  %s\n' "$B" "$N" "$col" "$1" "$N" "$msg"
  printf '%snext:%s    %s%s%s\n' "$B" "$N" "$C" "$2" "$N"
}
H=07fd8c3817607d93da0000d04085a0bbbfff3462f659f6054c901615c75c03a1

title "OK · clean PDF"
head5 "brief.pdf" "PDF document, version 1.5" "application/pdf" 101736 $H
plain "Pages: 4"; row "links:" "3 (do not follow them)"; blank
verdict OK "tools/q-convert.sh QUARANTINE/sender/brief.pdf"

title "OK · Word document"
head5 "requirements.docx" "Microsoft Word 2007+" "application/vnd.openxmlformats-officedocument.wordprocessingml.document" 9813 $H
blank
verdict OK "tools/q-convert.sh QUARANTINE/sender/requirements.docx"

title "OK · text or CSV"
head5 "data.csv" "CSV text" "text/csv" 2048 $H
blank
verdict OK "tools/q-convert.sh QUARANTINE/sender/data.csv"

title "OK · image"
head5 "screenshot.png" "PNG image data, 1920 x 1080, 8-bit/color RGBA" "image/png" 384201 $H
blank
verdict OK "tools/q-convert.sh QUARANTINE/sender/screenshot.png"

title "OK · plain archive"
head5 "dataset.tar.gz" "gzip compressed data, from Unix" "application/gzip" 52311 $H
row "entries:" "3"
listing "-rw-rw-r--  0 user group   48211 Nov 19 22:27 measurements.csv"
listing "-rw-rw-r--  0 user group    1204 Nov 19 22:27 README.txt"
listing "-rw-rw-r--  0 user group   90112 Nov 19 22:27 figure.png"
blank
verdict OK "tools/q-extract.sh QUARANTINE/sender/dataset.tar.gz"

title "CAUTION · PDF with active content"
head5 "document.pdf" "PDF document, version 1.7" "application/pdf" 245100 $H
plain "Pages: 2"; row "links:" "1 (do not follow them)"; blank
finding "PDF marker /JavaScript (2)"; finding "PDF marker /OpenAction (1)"; finding "PDF marker /EmbeddedFile (1)"; blank
verdict CAUTION "tools/q-convert.sh QUARANTINE/sender/document.pdf"

title "CAUTION · Office file with macros"
head5 "budget.xlsm" "Microsoft Excel 2007+" "application/vnd.ms-excel.sheet.macroenabled.12" 48120 $H
blank
finding "active content inside: xl/vbaProject.bin"; finding "macro-enabled format"; blank
verdict CAUTION "tools/q-convert.sh QUARANTINE/sender/budget.xlsm"

title "CAUTION · Office file loading a remote template"
head5 "report.docx" "Microsoft Word 2007+" "application/vnd.openxmlformats-officedocument.wordprocessingml.document" 15322 $H
blank
finding "loads content from outside the file: a remote template, object or linked data"; blank
verdict CAUTION "tools/q-convert.sh QUARANTINE/sender/report.docx"

title "CAUTION · archive containing code"
head5 "code-sample.zip" "Zip archive data, at least v2.0 to extract" "application/zip" 18230 $H
row "entries:" "57"
listing "-rw-r--r--  0 0 0     812 Nov 18 10:02 package.json"
listing "-rw-r--r--  0 0 0    4410 Nov 18 10:02 src/index.js"
listing "-rw-r--r--  0 0 0     233 Nov 18 10:02 .pre-commit-config.yaml"
listing "... 54 more"
blank
finding "contains code: after extracting, use the sandbox shell, never run on the host"; blank
verdict CAUTION "tools/q-extract.sh QUARANTINE/sender/code-sample.zip"

title "CAUTION · a script"
head5 "task.py" "Python script, ASCII text executable" "text/x-script.python" 1422 $H
blank
finding "source code: read it, never run it on the host"; blank
verdict CAUTION "tools/q-shell.sh QUARANTINE/sender"

title "CAUTION · HTML or SVG"
head5 "diagram.svg" "SVG Scalable Vector Graphics image" "image/svg+xml" 8843 $H
blank
finding "HTML/SVG can carry scripts: never open it in the browser"; blank
verdict CAUTION "tools/q-convert.sh QUARANTINE/sender/diagram.svg"

title "CAUTION · unrecognised type"
head5 "model.bin" "data" "application/octet-stream" 733120 $H
blank
finding "unrecognised file type"; blank
verdict CAUTION "ask the sender what this is; do not open it"

title "STOP · executable disguised as a PDF"
head5 "brief.pdf" "ELF 64-bit LSB pie executable, x86-64, dynamically linked, stripped" "application/x-pie-executable" 35208 $H
blank
finding "name says pdf, contents are executable: a disguised file"; finding "this is a program or installer, not a document"; blank
verdict STOP "rm -- QUARANTINE/sender/brief.pdf"

title "STOP · launcher with a double extension"
head5 "invoice.pdf.desktop" "ASCII text" "text/plain" 61 $H
blank
finding "double extension in the name"; finding "launcher file: runs a command when opened"; blank
verdict STOP "rm -- QUARANTINE/sender/invoice.pdf.desktop"

title "STOP · installer"
head5 "video-call-app.deb" "Debian binary package (format 2.0)" "application/vnd.debian.binary-package" 9120044 $H
blank
finding "this is a program or installer, not a document"; blank
verdict STOP "rm -- QUARANTINE/sender/video-call-app.deb"

title "STOP · archive containing an executable"
head5 "project-files.zip" "Zip archive data, at least v2.0 to extract" "application/zip" 2210344 $H
row "entries:" "2"
listing "-rw-r--r--  0 0 0    1200 Nov 18 10:02 README.txt"
listing "-rw-r--r--  0 0 0 2209001 Nov 18 10:02 setup.exe"
blank
finding "contains executables or launchers: setup.exe"; blank
verdict STOP "rm -- QUARANTINE/sender/project-files.zip"

title "STOP · password-protected archive"
head5 "documents.zip" "Zip archive data, at least v2.0 to extract" "application/zip" 40112 $H
row "entries:" "1"
listing "-rw-r--r--  0 0 0   39800 Nov 18 10:02 document.pdf"
blank
finding "password-protected archive (the usual way to slip past scanners)"; blank
verdict STOP "rm -- QUARANTINE/sender/documents.zip"
[ $show = 1 ] && echo
exit 0
