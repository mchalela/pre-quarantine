"""q-convert.sh and q-extract.sh: what lands on disk, and where."""
import stat

import samples


def test_pdf_becomes_png_pages_and_text_in_clean(box):
    result = box.run("q-convert.sh", box.put("brief.pdf", samples.pdf("Hello quarantine")))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.clean / "brief.pdf"
    assert (out / "page-001.png").read_bytes().startswith(samples.PNG_MAGIC)
    assert "Hello quarantine" in (out / "text.txt").read_text()


def test_docx_is_rendered_through_the_office_converter(box):
    result = box.run("q-convert.sh", box.put("notes.docx", samples.docx("Hello from docx")))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.clean / "notes.docx"
    assert (out / "page-001.png").read_bytes().startswith(samples.PNG_MAGIC)
    assert "Hello from docx" in (out / "text.txt").read_text()


def test_text_is_copied_as_text(box):
    box.run("q-convert.sh", box.put("data.csv", b"a,b\n1,2\n"))
    assert (box.clean / "data.csv" / "content.txt").read_text() == "a,b\n1,2\n"


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


def test_output_folder_name_is_sanitised(box):
    box.run("q-convert.sh", box.put("we ird;$(x).csv", b"a\n"))
    assert [p.name for p in box.clean.iterdir()] == ["we_ird___x_.csv"]


def test_extract_stays_in_quarantine_drops_symlinks_and_exec_bits(box):
    archive = samples.tar_gz({"run.sh": b"#!/bin/sh\necho hi\n", "notes.txt": b"x\n"},
                             symlinks={"passwd": "/etc/passwd"}, executable=("run.sh",))
    result = box.run("q-extract.sh", box.put("pack.tar.gz", archive))
    assert result.returncode == 0, result.stdout + result.stderr
    out = box.quarantine / "sender" / "pack.tar.gz.extracted"
    assert sorted(p.name for p in out.iterdir()) == ["notes.txt", "run.sh"]
    assert not any(p.is_symlink() for p in out.rglob("*"))
    for p in out.rglob("*"):
        if p.is_file():
            assert not p.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), p
    assert list(box.clean.iterdir()) == []


def test_extract_cannot_write_outside_its_folder(box):
    archive = samples.tar_gz({"../escape.txt": b"x", "/abs-escape.txt": b"x", "ok.txt": b"x"})
    box.run("q-extract.sh", box.put("evil.tar.gz", archive))
    out = box.quarantine / "sender" / "evil.tar.gz.extracted"
    everything = {p for p in box.root.rglob("*escape*")}
    assert all(out in p.parents for p in everything), everything
    assert (out / "ok.txt").exists()


def test_extract_refuses_to_overwrite_an_earlier_extraction(box):
    f = box.put("pack.tar.gz", samples.tar_gz({"a.txt": b"x"}))
    assert box.run("q-extract.sh", f).returncode == 0
    again = box.run("q-extract.sh", f)
    assert again.returncode != 0 and "already exists" in again.stderr
