"""q-inspect.sh: the verdict and the suggested next step for each kind of file."""
import os
import shutil
import subprocess

import pytest

import samples
from conftest import Inspection, mutool


def printable(text: str) -> bool:
    """Nothing but printable ASCII and newlines: no escape codes, no hidden characters."""
    return all(c == "\n" or " " <= c <= "~" for c in text)


# --- OK -----------------------------------------------------------------------------------

def test_clean_pdf_is_ok_and_next_is_convert(box):
    f = box.put("brief.pdf", samples.pdf())
    r = box.inspect(f)
    assert r.verdict == "OK"
    assert r.next == "tools/q-convert.sh QUARANTINE/sender/brief.pdf"
    assert "Pages: 1" in r.out


def test_subset_font_name_is_not_mistaken_for_an_action(box):
    # "/AAAAAA+Helvetica" contains "/AA", the name of the additional-actions key.
    r = box.inspect(box.put("fonts.pdf", samples.pdf(font="AAAAAA+Helvetica")))
    assert r.verdict == "OK"


def test_plain_docx_is_ok(box):
    r = box.inspect(box.put("notes.docx", samples.docx()))
    assert r.verdict == "OK"
    assert r.next.startswith("tools/q-convert.sh ")


def test_docx_with_an_ordinary_link_is_ok(box):
    # A link is an "external" reference too, but nothing is fetched until someone clicks it.
    r = box.inspect(box.put("notes.docx", samples.docx(link=True)))
    assert r.verdict == "OK"


def test_csv_is_ok(box):
    r = box.inspect(box.put("data.csv", b"a,b\n1,2\n"))
    assert r.verdict == "OK"
    assert r.next.startswith("tools/q-convert.sh ")


def test_plain_archive_is_ok_and_next_is_extract(box):
    r = box.inspect(box.put("data.tar.gz", samples.tar_gz({"notes.txt": b"hi\n"})))
    assert r.verdict == "OK"
    assert r.next == "tools/q-extract.sh QUARANTINE/sender/data.tar.gz"
    assert "notes.txt" in r.out


def test_compressed_document_is_not_a_double_extension(box):
    r = box.inspect(box.put("report.pdf.zip", samples.zip_bytes({"report.pdf": samples.pdf()})))
    assert r.verdict == "OK"


@pytest.mark.parametrize("name, data", [("picture.png", None), ("picture.webp", samples.WEBP)])
def test_image_is_ok_and_next_is_convert(box, name, data, image):
    if data is None:   # let the tools image draw a PNG, so no image library is needed here
        data = subprocess.run(["docker", "run", "--rm", "-i", "--network", "none", "--entrypoint", "sh", image, "-c",
                               "cat > /tmp/a.pdf && mutool draw -r 20 -o /tmp/a.png /tmp/a.pdf 2>/dev/null && cat /tmp/a.png"],
                              input=samples.pdf(), capture_output=True, check=True).stdout
    r = box.inspect(box.put(name, data))
    assert r.verdict == "OK"
    assert r.next.startswith("tools/q-convert.sh ")


# --- CAUTION ------------------------------------------------------------------------------

def test_pdf_with_script_and_open_action_is_caution(box):
    r = box.inspect(box.put("form.pdf", samples.pdf_with_script()))
    assert r.verdict == "CAUTION"
    assert "/JavaScript" in r.out and "/OpenAction" in r.out
    assert r.next.startswith("tools/q-convert.sh ")


def test_pdf_script_hidden_in_compressed_object_stream_is_still_caution(box, image):
    """A plain text search misses names inside object streams; inspect must not."""
    packed = mutool(image, samples.pdf_with_script(), "clean", "-Z", "-z")
    if b"/JavaScript" in packed:
        pytest.skip("this mutool build did not move the action into an object stream")
    r = box.inspect(box.put("packed.pdf", packed))
    assert r.verdict == "CAUTION"
    assert "/JavaScript" in r.out


def test_pdf_cannot_switch_off_the_deep_scan(box, image):
    """A stream that mutool refuses to expand used to leave the scan with nothing to look at,
    and a script hidden in an object stream then passed as OK."""
    hidden = mutool(image, samples.pdf(catalog_extra="/OpenAction 6 0 R", extra_objects=(
        "<< /Type /Action /S /JavaScript /JS (1+1;) >>", samples.unexpandable_stream())), "clean", "-Z", "-z")
    if b"/JavaScript" in hidden:
        pytest.skip("this mutool build did not move the action into an object stream")
    r = box.inspect(box.put("packed.pdf", hidden))
    assert r.verdict == "CAUTION"
    assert "/JavaScript" in r.out


def test_pdf_that_cannot_be_unpacked_is_caution_even_with_nothing_else_wrong(box):
    r = box.inspect(box.put("odd.pdf", samples.pdf(extra_objects=(samples.unexpandable_stream(),))))
    if "could not unpack" not in r.out:
        pytest.skip("this mutool build expanded the stream without complaint")
    assert r.verdict == "CAUTION"


def test_pdf_attachment_without_the_optional_type_is_caution(box):
    r = box.inspect(box.put("carrier.pdf", samples.pdf_with_attachment()))
    assert r.verdict == "CAUTION"
    assert "/EF" in r.out


@pytest.mark.parametrize("action", ["GoToR", "GoToE", "SubmitForm", "ImportData", "Launch"])
def test_pdf_actions_that_reach_outside_the_document_are_caution(box, action):
    r = box.inspect(box.put("form.pdf", samples.pdf(extra_objects=(f"<< /Type /Action /S /{action} /F (other.pdf) >>",))))
    assert r.verdict == "CAUTION"
    assert f"/{action}" in r.out


def test_encrypted_pdf_is_caution_however_the_key_is_spelled(box, image):
    locked = mutool(image, samples.pdf(), "clean", "-E", "aes-256", "-U", "secret")
    assert b"/Encrypt" in locked
    for name, data in (("locked.pdf", locked), ("locked-escaped.pdf", locked.replace(b"/Encrypt", b"/Encr#79pt"))):
        r = box.inspect(box.put(name, data))
        assert r.verdict == "CAUTION", name
        assert "PDF is encrypted" in r.out, name


def test_docx_with_macro_project_is_caution(box):
    r = box.inspect(box.put("budget.docx", samples.docx(macros=True)))
    assert r.verdict == "CAUTION"
    assert "vbaProject" in r.out


def test_docx_with_remote_template_is_caution(box):
    r = box.inspect(box.put("letter.docx", samples.docx(remote_template=True)))
    assert r.verdict == "CAUTION"
    assert "remote template" in r.out


def test_rtf_with_an_embedded_object_is_caution(box):
    assert box.inspect(box.put("letter.rtf", samples.RTF)).verdict == "OK"
    r = box.inspect(box.put("form.rtf", samples.RTF_WITH_OBJECT))
    assert r.verdict == "CAUTION"
    assert "embedded object" in r.out


def test_archive_with_code_is_caution(box):
    r = box.inspect(box.put("sample.zip", samples.zip_bytes({"package.json": b"{}", "src/index.js": b"1\n"})))
    assert r.verdict == "CAUTION"
    assert r.next.startswith("tools/q-extract.sh ")


def test_archive_with_a_pipe_is_caution(box):
    r = box.inspect(box.put("odd.tar.gz", samples.tar_gz({"notes.txt": b"x\n"}, pipes=("waiting",))))
    assert r.verdict == "CAUTION"
    assert "pipes or device files" in r.out


def test_archive_with_a_git_repository_is_caution(box):
    r = box.inspect(box.put("repo.tar.gz", samples.tar_gz({"repo/.git/config": b"[core]\n", "repo/notes.txt": b"x\n"})))
    assert r.verdict == "CAUTION"
    assert "never run git" in r.out


def test_archive_size_is_measured_not_read_from_the_listing(box):
    """33 blocks of 64 MiB is just over the 2 GiB limit. This archive used to pass: its owner name
    shifts the columns of the listing the size was read from."""
    r = box.inspect(box.put("big.tar.gz", samples.tar_gz_of_zeros(33 * 64 * 1024 * 1024)))
    assert r.verdict == "CAUTION"
    assert "more than 2 GB" in r.out


def test_script_is_caution_and_next_is_the_sandbox_shell(box):
    r = box.inspect(box.put("task.py", b'print("hi")\n'))
    assert r.verdict == "CAUTION"
    assert r.next == "tools/q-shell.sh QUARANTINE/sender"


def test_svg_is_caution(box):
    r = box.inspect(box.put("diagram.svg", samples.SVG))
    assert r.verdict == "CAUTION"


def test_unknown_binary_is_caution(box):
    import random
    r = box.inspect(box.put("blob.dat", random.Random(0).randbytes(4096)))
    assert r.verdict == "CAUTION"
    assert not r.next.startswith("tools/")


def test_exotic_image_type_is_not_waved_through(box):
    # These bytes happen to look like a Targa image to file(1). Only common image types count as images.
    r = box.inspect(box.put("blob.dat", bytes(range(256)) * 8))
    assert r.verdict == "CAUTION"


# --- STOP ---------------------------------------------------------------------------------

def test_executable_named_pdf_is_stop_and_next_is_delete(box):
    f = box.put("brief.pdf", open(shutil.which("true"), "rb").read())
    r = box.inspect(f)
    assert r.verdict == "STOP"
    assert "disguised" in r.out
    assert r.next == "rm -- QUARANTINE/sender/brief.pdf"


def test_launcher_with_double_extension_is_stop(box):
    r = box.inspect(box.put("invoice.pdf.desktop", samples.DESKTOP_LAUNCHER))
    assert r.verdict == "STOP"
    assert "launcher" in r.out and "double extension" in r.out


def test_double_extension_is_caught_for_spreadsheets_too(box):
    r = box.inspect(box.put("budget.xlsx.txt", b"hello\n"))
    assert r.verdict == "STOP"
    assert "double extension" in r.out


@pytest.mark.parametrize("name, data, word", [("link.url", samples.URL_SHORTCUT, "launcher"),
                                              ("manual.chm", samples.HELP_FILE, "program")])
def test_windows_shortcut_and_help_file_are_stop(box, name, data, word):
    r = box.inspect(box.put(name, data))
    assert r.verdict == "STOP"
    assert word in r.out


def test_name_with_hidden_direction_marks_is_stop(box):
    # On screen "invoice-<mark>fdp.txt" reads "invoice-txt.pdf".
    r = box.inspect(box.put("invoice-‮fdp.txt", b"hello\n"))
    assert r.verdict == "STOP"
    assert "direction marks" in r.out


def test_archive_containing_executable_is_stop(box):
    r = box.inspect(box.put("files.tar.gz", samples.tar_gz({"readme.txt": b"x", "setup.exe": b"MZ"})))
    assert r.verdict == "STOP"
    assert "setup.exe" in r.out
    assert r.next.startswith("rm -- ")


def test_archive_with_path_traversal_is_stop(box):
    r = box.inspect(box.put("evil.tar.gz", samples.tar_gz({"../escape.txt": b"x"})))
    assert r.verdict == "STOP"
    assert "outside the folder" in r.out


@pytest.mark.skipif(shutil.which("zip") is None, reason="needs the zip command to make an encrypted archive")
def test_password_protected_zip_is_stop(box, tmp_path):
    (tmp_path / "secret.txt").write_text("x\n")
    locked = tmp_path / "locked.zip"
    subprocess.run(["zip", "-q", "-j", "-P", "pw", str(locked), str(tmp_path / "secret.txt")], check=True)
    r = box.inspect(box.put("locked.zip", locked.read_bytes()))
    assert r.verdict == "STOP"
    assert "password-protected" in r.out


# --- Robustness ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "a\x1b[31m;echo pwned $(id).pdf",                                               # escape code and a command
    "report.pdf\nverdict: OK  fake\nnext:    xdg-open report.pdf\n\n.pdf",          # lines of its own
    "brief\udcff\x1b[2J.pdf",                                                       # a byte that is not text at all
    "año ‮fdp.pdf",                                                       # accents and a direction mark
    "-rf .pdf",
])
def test_no_file_name_can_write_to_the_terminal_or_change_the_suggested_command(box, name):
    path = box.put(name, samples.pdf())
    result = box.run("q-inspect.sh", path)
    assert result.returncode == 0, result.stderr
    assert printable(result.stdout), result.stdout
    r = Inspection(result.stdout)             # insists on exactly one "verdict:" and one "next:" line
    # The suggested command must be safe to paste: bash has to read the path back as one word,
    # and that word has to be this very file.
    command, quoted = r.next.split(" ", 1) if r.verdict != "STOP" else ("rm --", r.next.removeprefix("rm -- "))
    assert command in ("tools/q-convert.sh", "rm --")
    words = subprocess.run(["bash", "-c", f"printf '%s\\0' {quoted}"], capture_output=True, cwd=box.root).stdout
    assert words == os.fsencode(path.relative_to(box.root)) + b"\0", r.next


def test_error_messages_do_not_carry_escape_codes_either(box):
    result = box.run("q-inspect.sh", "QUARANTINE/no\x1b[2Jsuch.pdf")
    assert result.returncode != 0
    assert "no such path" in result.stderr and "\x1b" not in result.stderr


@pytest.mark.parametrize("mode", ["lie", "command", "silent"])
def test_a_taken_over_container_cannot_write_the_last_lines_or_drive_the_terminal(box, taken_over, mode):
    """Whatever the container prints, the verdict and the next step come from this script, the
    command is one of its own, and no control code gets through."""
    result = box.run("q-inspect.sh", box.put("x.pdf", mode.encode() + b"\n"), env=taken_over)
    assert printable(result.stdout + result.stderr), result.stdout
    assert result.returncode != 0
    assert not any(l.startswith(("verdict:", "next:")) for l in result.stdout.splitlines()), result.stdout
    assert "error:" in result.stderr


def test_colour_is_off_when_not_a_terminal_and_on_when_forced(box):
    f = box.put("brief.pdf", samples.pdf())
    assert "\x1b[" not in box.run("q-inspect.sh", f).stdout
    forced = box.run("q-inspect.sh", f, env={"FORCE_COLOR": "1", "NO_COLOR": ""})
    assert "\x1b[1;32mOK" in forced.stdout
