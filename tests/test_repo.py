"""Repository-level guarantees: nothing untrusted is committed, the agent stays fenced in,
the base image is one that still gets fixes, and the demo stays in step with the real tool."""
import datetime
import json
import re
import subprocess

from conftest import REPO


def ignored(path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO).returncode == 0


def test_quarantine_and_clean_contents_are_never_tracked():
    assert ignored("QUARANTINE/sender/file.pdf") and ignored("CLEAN/sender/file.pdf/page-001.png")
    assert ignored("QUARANTINE/.q-abc123/page-001.png")          # scratch folders of the scripts
    assert not ignored("QUARANTINE/.gitkeep") and not ignored("CLEAN/.gitkeep")
    tracked = subprocess.run(["git", "ls-files", "QUARANTINE", "CLEAN"], cwd=REPO,
                             capture_output=True, text=True).stdout.split()
    assert sorted(tracked) == ["CLEAN/.gitkeep", "QUARANTINE/.gitkeep"]


def test_agent_permissions_fence_off_quarantine_the_tools_and_the_web():
    settings = json.loads((REPO / "agent" / "settings.json").read_text())
    perms = settings["permissions"]
    deny, allow = perms["deny"], perms["allow"]
    for rule in ("Read(./QUARANTINE/**)", "Edit(./QUARANTINE/**)", "Edit(./tools/**)", "Edit(./agent/**)",
                 "Edit(./.claude/**)", "Edit(./CLAUDE.md)", "WebFetch", "WebSearch"):
        assert rule in deny, rule
    assert perms["defaultMode"] == "default"
    assert perms["disableBypassPermissionsMode"] == "disable"
    assert not any("q-shell" in rule or "install-agent-rules" in rule or rule in ("Bash", "Bash(*)")
                   for rule in allow)


def test_agent_has_no_side_doors():
    """Ways around the fence that need no file access: other tools, other agents, other modes,
    and notes or instruction files that outlive the session or come from a sender."""
    settings = json.loads((REPO / "agent" / "settings.json").read_text())
    perms = settings["permissions"]
    for rule in ("mcp__*", "Agent", "Bash(./tools/q-shell.sh:*)", "Bash(./tools/install-agent-rules.sh:*)"):
        assert rule in perms["deny"], rule
    assert perms["disableAutoMode"] == "disable"
    assert settings["autoMemoryEnabled"] is False
    assert {"**/QUARANTINE/**", "**/CLEAN/**"} <= set(settings["claudeMdExcludes"])
    # Path rules for the Write tool match nothing (Edit rules cover it), so one would only look like a fence.
    assert not any(rule.startswith("Write(") for rule in perms["deny"] + perms["allow"])


def test_agent_rules_ship_as_templates_and_are_never_active_in_the_repo():
    """A checkout must not bind a development agent: the active locations are untracked and ignored."""
    tracked = subprocess.run(["git", "ls-files", "CLAUDE.md", ".claude"], cwd=REPO,
                             capture_output=True, text=True).stdout.split()
    assert tracked == []
    assert ignored("CLAUDE.md") and ignored(".claude/settings.json")
    assert not ignored("agent/CLAUDE.md") and not ignored("agent/settings.json")


def test_base_image_still_gets_security_fixes():
    """The parsers in the image are the attack surface. When this fails, the Alpine branch has
    reached the end of its support: move tools/image/Dockerfile to a current branch and set the
    new end date in tools/build.sh (https://alpinelinux.org/releases/)."""
    dockerfile = (REPO / "tools" / "image" / "Dockerfile").read_text()
    assert re.search(r"^FROM alpine:\d+\.\d+$", dockerfile, re.M), "pin the base image to an Alpine branch"
    until = re.search(r"^SUPPORTED_UNTIL=(\d{4}-\d{2}-\d{2})$", (REPO / "tools" / "build.sh").read_text(), re.M)
    assert until, "tools/build.sh must record when support for the base image ends"
    assert datetime.date.today() < datetime.date.fromisoformat(until.group(1))


def test_readme_command_for_emptying_both_folders_spares_only_the_two_placeholders(tmp_path):
    """The command is pasted as it stands, so it is run here as it stands. An earlier version
    spared every file called .gitkeep, at any depth: a name a sender is free to use."""
    command = re.search(r"`(find QUARANTINE CLEAN [^`]*-delete)`", (REPO / "README.md").read_text()).group(1)
    for top in ("QUARANTINE", "CLEAN"):
        (tmp_path / top / "sender" / "deep").mkdir(parents=True)
        (tmp_path / top / ".gitkeep").touch()
        (tmp_path / top / "sender" / ".gitkeep").write_text("not a placeholder\n")
        (tmp_path / top / "sender" / "deep" / ".hidden").touch()
        (tmp_path / top / ".q-abc123").mkdir()
    subprocess.run(["bash", "-c", command], cwd=tmp_path, check=True)
    left = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert left == ["CLEAN", "CLEAN/.gitkeep", "QUARANTINE", "QUARANTINE/.gitkeep"]


def test_links_between_the_readme_and_the_docs_point_at_files_that_exist():
    pages = [REPO / "README.md", *sorted((REPO / "docs").glob("*.md"))]
    assert len(pages) > 1
    for page in pages:
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", page.read_text()):
            if "://" not in target:
                assert (page.parent / target).exists(), f"{page.relative_to(REPO)} links to {target}"


def test_demo_runs_and_uses_the_real_verdict_wording():
    demo = subprocess.run([str(REPO / "tools" / "demo-inspect.sh")], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)
    assert demo.returncode == 0
    real = (REPO / "tools" / "q-inspect.sh").read_text()
    messages = {line.split(None, 2)[2] for line in demo.stdout.splitlines() if line.startswith("verdict:")}
    assert len(messages) == 3
    for message in messages:
        assert message in real, f"demo wording drifted from tools/q-inspect.sh: {message!r}"
