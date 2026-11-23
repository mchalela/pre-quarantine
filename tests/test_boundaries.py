"""The scripts only ever act on files inside QUARANTINE/."""
import pytest

import samples

SCRIPTS = ["q-inspect.sh", "q-convert.sh", "q-extract.sh"]


@pytest.mark.parametrize("script", SCRIPTS)
def test_refuses_a_path_outside_quarantine(box, script):
    result = box.run(script, "/etc/hostname")
    assert result.returncode != 0
    assert "refusing" in result.stderr


@pytest.mark.parametrize("script", SCRIPTS)
def test_refuses_a_symlink_that_points_out_of_quarantine(box, script, tmp_path):
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(samples.pdf())
    link = box.quarantine / "link.pdf"
    link.symlink_to(outside)
    result = box.run(script, link)
    assert result.returncode != 0
    assert "refusing" in result.stderr


@pytest.mark.parametrize("script", SCRIPTS)
def test_refuses_dot_dot_out_of_quarantine(box, script):
    (box.root / "secret.txt").write_text("x")
    result = box.run(script, "QUARANTINE/../secret.txt")
    assert result.returncode != 0


def test_shell_refuses_a_folder_outside_quarantine(box):
    result = box.run("q-shell.sh", box.clean, "--", "true")
    assert result.returncode != 0
    assert "refusing" in result.stderr


def test_missing_file_is_an_error_not_a_crash(box):
    result = box.run("q-inspect.sh", "QUARANTINE/nope.pdf")
    assert result.returncode != 0
    assert "no such path" in result.stderr


@pytest.mark.parametrize("script", SCRIPTS)
def test_refuses_an_image_that_was_not_built_from_these_scripts(box, script):
    """After a git pull the old image is still there. Its output would be misread, so it is not used."""
    result = box.run(script, box.put("brief.pdf", samples.pdf()), env={"Q_IMAGE": "python:3.12-slim"})
    assert result.returncode != 0
    assert "tools/build.sh" in result.stderr
    assert list(box.clean.iterdir()) == []
