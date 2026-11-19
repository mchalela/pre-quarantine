"""q-inspect.sh: the verdict and the suggested next step for each kind of file."""
import shutil
import subprocess

import pytest

import samples


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


def test_csv_is_ok(box):
    r = box.inspect(box.put("data.csv", b"a,b\n1,2\n"))
    assert r.verdict == "OK"
    assert r.next.startswith("tools/q-convert.sh ")


def test_plain_archive_is_ok_and_next_is_extract(box):
    r = box.inspect(box.put("data.tar.gz", samples.tar_gz({"notes.txt": b"hi\n"})))
    assert r.verdict == "OK"
    assert r.next == "tools/q-extract.sh QUARANTINE/sender/data.tar.gz"
    assert "notes.txt" in r.out


# --- CAUTION ------------------------------------------------------------------------------

def test_pdf_with_script_and_open_action_is_caution(box):
    r = box.inspect(box.put("form.pdf", samples.pdf_with_script()))
    assert r.verdict == "CAUTION"
    assert "/JavaScript" in r.out and "/OpenAction" in r.out
    assert r.next.startswith("tools/q-convert.sh ")


def test_pdf_script_hidden_in_compressed_object_stream_is_still_caution(box, image):
    """A plain text search misses names inside object streams; inspect must not."""
    packed = subprocess.run(
        ["docker", "run", "--rm", "-i", "--network", "none", "--entrypoint", "sh", image, "-c",
         "cat > /tmp/a.pdf && mutool clean -Z -z /tmp/a.pdf /tmp/b.pdf && cat /tmp/b.pdf"],
        input=samples.pdf_with_script(), capture_output=True, check=True).stdout
    if b"/JavaScript" in packed:
        pytest.skip("this mutool build did not move the action into an object stream")
    r = box.inspect(box.put("packed.pdf", packed))
    assert r.verdict == "CAUTION"
    assert "/JavaScript" in r.out


def test_docx_with_macro_project_is_caution(box):
    r = box.inspect(box.put("budget.docx", samples.docx(macros=True)))
    assert r.verdict == "CAUTION"
    assert "vbaProject" in r.out


def test_docx_with_remote_template_is_caution(box):
    r = box.inspect(box.put("letter.docx", samples.docx(remote_template=True)))
    assert r.verdict == "CAUTION"
    assert "remote template" in r.out


def test_archive_with_code_is_caution(box):
    r = box.inspect(box.put("sample.zip", samples.zip_bytes({"package.json": b"{}", "src/index.js": b"1\n"})))
    assert r.verdict == "CAUTION"
    assert r.next.startswith("tools/q-extract.sh ")


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

def test_hostile_file_name_cannot_inject_terminal_codes_or_commands(box):
    name = "a\x1b[31m;echo pwned $(id).pdf"
    result = box.run("q-inspect.sh", box.put(name, samples.pdf()))
    assert result.returncode == 0
    assert "\x1b" not in result.stdout
    # The suggested command must be safe to paste: bash has to read the path back as one word.
    suggested = [l for l in result.stdout.splitlines() if l.startswith("next:")][0].split(None, 1)[1]
    words = subprocess.run(["bash", "-c", f'printf "%s\\n" {suggested} | wc -l'],
                           capture_output=True, text=True, cwd=box.root).stdout
    assert words.strip() == "2", suggested  # script + one path argument, nothing executed
    assert "pwned" not in subprocess.run(["bash", "-c", f": {suggested}"], capture_output=True, text=True).stdout


def test_colour_is_off_when_not_a_terminal_and_on_when_forced(box):
    f = box.put("brief.pdf", samples.pdf())
    assert "\x1b[" not in box.run("q-inspect.sh", f).stdout
    forced = box.run("q-inspect.sh", f, env={"FORCE_COLOR": "1", "NO_COLOR": ""})
    assert "\x1b[1;32mOK" in forced.stdout
