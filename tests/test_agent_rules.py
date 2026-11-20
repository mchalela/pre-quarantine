"""tools/install-agent-rules.sh: the rules become active only where the user activates them."""
import shutil
import subprocess

import pytest

import samples
from conftest import REPO, Box


@pytest.fixture
def install(tmp_path) -> Box:
    """A fresh working install: tools and agent templates, nothing activated yet."""
    root = tmp_path / "install"
    shutil.copytree(REPO / "tools", root / "tools")
    shutil.copytree(REPO / "agent", root / "agent")
    (root / "QUARANTINE").mkdir()
    (root / "CLEAN").mkdir()
    return Box(root)


def test_nothing_is_active_until_the_script_runs(install):
    assert not (install.root / "CLAUDE.md").exists()
    assert not (install.root / ".claude").exists()


def test_install_activates_exact_copies_of_the_templates(install):
    result = install.run("install-agent-rules.sh")
    assert result.returncode == 0, result.stderr
    assert (install.root / "CLAUDE.md").read_bytes() == (REPO / "agent" / "CLAUDE.md").read_bytes()
    assert ((install.root / ".claude" / "settings.json").read_bytes()
            == (REPO / "agent" / "settings.json").read_bytes())


def test_install_is_repeatable_and_refreshes_stale_copies(install):
    install.run("install-agent-rules.sh")
    (install.root / "CLAUDE.md").write_text("tampered\n")
    assert install.run("install-agent-rules.sh").returncode == 0
    assert (install.root / "CLAUDE.md").read_bytes() == (REPO / "agent" / "CLAUDE.md").read_bytes()


def test_remove_deactivates_and_leaves_the_templates(install):
    install.run("install-agent-rules.sh")
    assert install.run("install-agent-rules.sh", "--remove").returncode == 0
    assert not (install.root / "CLAUDE.md").exists()
    assert not (install.root / ".claude").exists()
    assert (install.root / "agent" / "CLAUDE.md").exists()


def test_unknown_option_is_rejected_without_changing_anything(install):
    result = install.run("install-agent-rules.sh", "--bogus")
    assert result.returncode == 2
    assert not (install.root / "CLAUDE.md").exists()


def test_tools_warn_when_active_rules_fall_behind_the_templates(install):
    f = install.put("brief.pdf", samples.pdf())
    install.run("install-agent-rules.sh")
    assert "out of date" not in install.run("q-inspect.sh", f).stderr

    (install.root / "agent" / "settings.json").write_text('{"permissions": {}}\n')   # as after a git pull
    stale = install.run("q-inspect.sh", f)
    assert stale.returncode == 0
    assert "out of date" in stale.stderr and "install-agent-rules.sh" in stale.stderr

    (install.root / ".claude" / "settings.json").unlink()                              # or deleted by one
    assert "out of date" in install.run("q-inspect.sh", f).stderr


def test_tools_stay_quiet_where_rules_were_never_activated(install):
    f = install.put("brief.pdf", samples.pdf())
    assert install.run("q-inspect.sh", f).stderr == ""
