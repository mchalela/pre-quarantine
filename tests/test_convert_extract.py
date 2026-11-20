"""q-convert.sh and q-extract.sh: what lands on disk, and where."""
import stat

import pytest

import samples


def plain_files_only(folder) -> bool:
    """No links, pipes or other special files anywhere below `folder`, and nothing executable."""
    for p in folder.rglob("*"):
        mode = p.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            return False
        if stat.S_ISREG(mode) and mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            return False
    return True


# --- convert ------------------------------------------------------------------------------

def test_pdf_becomes_png_pages_and_text_in_clean(box):
    result = box.run("q-convert.sh", box.put("brief.pdf", samples.pdf("Hello quarantine")))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.clean / "sender" / "brief.pdf"
    assert (out / "page-001.png").read_bytes().startswith(samples.PNG_MAGIC)
    assert "Hello quarantine" in (out / "text.txt").read_text()
    assert box.scratch_left() == []


def test_docx_is_rendered_through_the_office_converter(box):
    result = box.run("q-convert.sh", box.put("notes.docx", samples.docx("Hello from docx")))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.clean / "sender" / "notes.docx"
    assert (out / "page-001.png").read_bytes().startswith(samples.PNG_MAGIC)
    assert "Hello from docx" in (out / "text.txt").read_text()


def test_rtf_is_rendered_not_copied_as_text(box):
    result = box.run("q-convert.sh", box.put("letter.rtf", samples.RTF))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.clean / "sender" / "letter.rtf"
    assert (out / "page-001.png").read_bytes().startswith(samples.PNG_MAGIC)
    assert "Hello from rtf" in (out / "text.txt").read_text()
    assert not (out / "content.txt").exists()


def test_webp_image_is_rendered(box):
    result = box.run("q-convert.sh", box.put("picture.webp", samples.WEBP))
    assert result.returncode == 0, result.stdout + result.stderr
    assert (box.clean / "sender" / "picture.webp" / "page-001.png").read_bytes().startswith(samples.PNG_MAGIC)


def test_text_is_copied_as_text(box):
    box.run("q-convert.sh", box.put("data.csv", b"a,b\n1,2\n"))
    assert (box.clean / "sender" / "data.csv" / "content.txt").read_text() == "a,b\n1,2\n"


def test_text_copy_keeps_letters_but_loses_control_codes(box):
    # Escape codes in both spellings (ESC, and the single character U+009B) and a carriage return.
    hostile = "café\ttab \x1b[2Jone \u009b2Jtwo\rthree\n".encode()
    box.run("q-convert.sh", box.put("notes.txt", hostile))
    assert (box.clean / "sender" / "notes.txt" / "content.txt").read_text() == "café\ttab [2Jone 2Jtwothree\n"


def test_long_text_is_cut_and_the_script_says_so(box):
    result = box.run("q-convert.sh", box.put("long.txt", b"0123456789abcde\n" * 400_000))    # 6.4 MB
    assert result.returncode == 0
    assert "only the first 5 MB" in result.stdout
    assert (box.clean / "sender" / "long.txt" / "content.txt").stat().st_size == 5_000_000


def test_long_document_is_cut_at_500_pages_and_the_script_says_so(box):
    result = box.run("q-convert.sh", box.put("long.pdf", samples.pdf(pages=501)))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "only the first 500" in result.stdout
    pages = sorted(p.name for p in (box.clean / "sender" / "long.pdf").glob("page-*.png"))
    assert len(pages) == 500 and pages[-1] == "page-500.png"


def test_convert_never_changes_the_original(box):
    data = samples.pdf()
    f = box.put("brief.pdf", data)
    box.run("q-convert.sh", f)
    assert f.read_bytes() == data


def test_convert_refuses_an_executable_and_leaves_no_output_folder(box):
    import shutil
    result = box.run("q-convert.sh", box.put("tool.bin", open(shutil.which("true"), "rb").read()))
    assert result.returncode != 0
    assert list(box.clean.iterdir()) == []
    assert box.scratch_left() == []


def test_failed_conversion_leaves_nothing_behind_and_prints_no_escape_codes(box):
    """The page asks for a picture that does not exist, under a name with an escape code in it.
    mutool repeats that name in its error text."""
    broken = samples.pdf(content=b"q /Y\x1b#5B2JFAKE Do Q")      # "#5B" is how a PDF name spells "["
    result = box.run("q-convert.sh", box.put("broken.pdf", broken))
    if result.returncode == 0:
        pytest.skip("this mutool build renders the page in spite of the error")
    assert "\x1b" not in result.stdout + result.stderr
    assert list(box.clean.iterdir()) == []
    assert box.scratch_left() == []


def test_output_folder_name_is_sanitised(box):
    box.run("q-convert.sh", box.put("we ird;$(x).csv", b"a\n", sender="some one;$(y)"))
    assert [p.name for p in box.clean.iterdir()] == ["some_one___y_"]
    assert [p.name for p in (box.clean / "some_one___y_").iterdir()] == ["we_ird___x_.csv"]


def test_output_folder_is_never_hidden_or_shaped_like_an_option(box):
    box.run("q-convert.sh", box.put(".hidden.csv", b"a\n"))
    box.run("q-convert.sh", box.put("-rf.csv", b"a\n"))
    assert sorted(p.name for p in (box.clean / "sender").iterdir()) == ["_hidden.csv", "_rf.csv"]


def test_same_file_name_from_two_senders_stays_separate(box):
    box.run("q-convert.sh", box.put("cv.csv", b"first\n", sender="alpha"))
    box.run("q-convert.sh", box.put("cv.csv", b"second\n", sender="beta"))
    assert (box.clean / "alpha" / "cv.csv" / "content.txt").read_text() == "first\n"
    assert (box.clean / "beta" / "cv.csv" / "content.txt").read_text() == "second\n"


def test_only_the_sender_folder_is_mirrored_in_clean(box):
    deep = box.put("deep.csv", b"a\n", sender="sender/pack.zip.extracted/inner")
    box.run("q-convert.sh", deep)
    assert (box.clean / "sender" / "deep.csv" / "content.txt").exists()
    top = box.quarantine / "loose.csv"
    top.write_bytes(b"a\n")
    box.run("q-convert.sh", top)
    assert (box.clean / "loose.csv" / "content.txt").exists()
    assert sorted(p.name for p in box.clean.iterdir()) == ["loose.csv", "sender"]


def test_convert_never_writes_into_a_folder_that_is_already_there(box):
    """Converting a shorter file under the same name used to leave the old document's later pages
    next to the new first page, and two files with one name in different subfolders shared a folder."""
    first = box.put("terms.pdf", samples.pdf("OLD", pages=3))
    assert box.run("q-convert.sh", first).returncode == 0
    out = box.clean / "sender" / "terms.pdf"
    first.write_bytes(samples.pdf("NEW"))
    again = box.run("q-convert.sh", first)
    assert again.returncode != 0 and "already there" in again.stderr
    other = box.run("q-convert.sh", box.put("terms.pdf", samples.pdf("OTHER"), sender="sender/drafts"))
    assert other.returncode != 0 and "already there" in other.stderr
    assert sorted(p.name for p in out.iterdir()) == ["page-001.png", "page-002.png", "page-003.png", "text.txt"]
    assert "OLD" in (out / "text.txt").read_text()


@pytest.mark.parametrize("mode", ["link", "rules", "folder", "notpng", "pipe", "huge"])
def test_nothing_unexpected_from_a_taken_over_converter_reaches_clean(box, taken_over, mode):
    """A link to a host file, instructions for an agent, a script named like a page, a file that
    would fill the disk when copied: each one means the converter is no longer ours, and then
    nothing it wrote is kept."""
    result = box.run("q-convert.sh", box.put("x.pdf", mode.encode() + b"\n"), env=taken_over)
    assert result.returncode != 0
    assert "treat the original as hostile" in result.stderr
    assert "\x1b" not in result.stdout + result.stderr
    assert list(box.clean.iterdir()) == []
    assert box.scratch_left() == []


def test_what_a_taken_over_converter_may_keep_is_made_harmless(box, taken_over):
    result = box.run("q-convert.sh", box.put("a.pdf", b"modes\n"), env=taken_over)
    assert result.returncode == 0, result.stderr
    assert "\x1b" not in result.stdout and "\u009b" not in result.stdout
    assert plain_files_only(box.clean)
    box.run("q-convert.sh", box.put("b.pdf", b"codes\n"), env=taken_over)
    assert (box.clean / "sender" / "b.pdf" / "text.txt").read_text() == "a[2Jbcd\tkept\n"


# --- extract ------------------------------------------------------------------------------

def test_extract_stays_in_quarantine_drops_symlinks_and_exec_bits(box):
    archive = samples.tar_gz({"run.sh": b"#!/bin/sh\necho hi\n", "notes.txt": b"x\n"},
                             symlinks={"passwd": "/etc/passwd"}, executable=("run.sh",))
    result = box.run("q-extract.sh", box.put("pack.tar.gz", archive))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.quarantine / "sender" / "pack.tar.gz.extracted"
    assert sorted(p.name for p in out.iterdir()) == ["notes.txt", "run.sh"]
    assert plain_files_only(out)
    assert list(box.clean.iterdir()) == []
    assert box.scratch_left() == []


def test_extract_tidies_a_folder_the_archive_tried_to_lock(box):
    """A folder with no permissions used to stop the clean-up: the link and the exec bit inside it
    stayed, and so did a pipe."""
    archive = samples.tar_gz({"notes.txt": b"x\n", "closed/run.sh": b"#!/bin/sh\necho hi\n"},
                             folders={"closed": 0o000}, symlinks={"closed/inner": "/etc/hostname"},
                             executable=("closed/run.sh",), pipes=("waiting",))
    result = box.run("q-extract.sh", box.put("pack.tar.gz", archive))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.quarantine / "sender" / "pack.tar.gz.extracted"
    assert sorted(str(p.relative_to(out)) for p in out.rglob("*")) == ["closed", "closed/run.sh", "notes.txt"]
    assert plain_files_only(out)


def test_extract_does_not_rely_on_the_container_to_tidy_up(box, taken_over):
    result = box.run("q-extract.sh", box.put("pack.tar.gz", b"anything\n"), env=taken_over)
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.quarantine / "sender" / "pack.tar.gz.extracted"
    assert sorted(str(p.relative_to(out)) for p in out.rglob("*")) == ["closed", "closed/inner.sh", "sub", "sub/run.sh"]
    assert plain_files_only(out)


def test_extract_cannot_write_outside_its_folder(box):
    archive = samples.tar_gz({"../escape.txt": b"x", "/abs-escape.txt": b"x", "ok.txt": b"x"})
    result = box.run("q-extract.sh", box.put("evil.tar.gz", archive))
    out = box.quarantine / "sender" / "evil.tar.gz.extracted"
    everything = {p for p in box.root.rglob("*escape*")}
    assert all(out in p.parents for p in everything), everything
    assert (out / "ok.txt").exists()
    # The archive did not unpack cleanly, and the script must say so instead of reporting success.
    assert result.returncode != 0 and "did not unpack cleanly" in result.stderr


def test_extract_refuses_to_overwrite_an_earlier_extraction(box):
    f = box.put("pack.tar.gz", samples.tar_gz({"a.txt": b"x"}))
    assert box.run("q-extract.sh", f).returncode == 0
    again = box.run("q-extract.sh", f)
    assert again.returncode != 0 and "already exists" in again.stderr


def test_extract_refuses_a_decompression_bomb_unless_told_it_is_expected(box):
    f = box.put("big.tar.gz", samples.tar_gz_of_zeros(33 * 64 * 1024 * 1024))
    result = box.run("q-extract.sh", f)
    assert result.returncode != 0
    assert "more than 2 GB" in result.stdout and "--big" in result.stdout
    assert not (box.quarantine / "sender" / "big.tar.gz.extracted").exists()
    assert box.scratch_left() == []
    # The option is accepted; a small archive is used so that no test writes gigabytes to disk.
    small = box.put("small.tar.gz", samples.tar_gz({"a.txt": b"x"}))
    assert box.run("q-extract.sh", small, "--big").returncode == 0
    assert box.run("q-extract.sh", small, "--huge").returncode != 0


def test_extract_points_out_a_git_repository(box):
    archive = samples.tar_gz({"repo/.git/config": b"[core]\n", "repo/notes.txt": b"x\n"})
    result = box.run("q-extract.sh", box.put("repo.tar.gz", archive))
    assert result.returncode == 0, result.stderr
    assert "Never run git" in result.stdout


def test_extract_works_from_a_folder_with_an_awkward_name(box):
    """Folder names inside an extracted archive are the sender's choice. They must not end up in
    the options handed to docker, where a colon or a comma means something."""
    inner = box.put("inner.tar.gz", samples.tar_gz({"a.txt": b"x"}), sender="sender/odd:name,rw")
    result = box.run("q-extract.sh", inner)
    assert result.returncode == 0, result.stderr
    assert (inner.parent / "inner.tar.gz.extracted" / "a.txt").exists()
