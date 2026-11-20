"""Repository-level guarantees: nothing untrusted is committed, the agent stays fenced in,
and the demo stays in step with the real tool."""
import json
import subprocess

from conftest import REPO


def ignored(path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO).returncode == 0


def test_quarantine_and_clean_contents_are_never_tracked():
    assert ignored("QUARANTINE/sender/file.pdf") and ignored("CLEAN/file.pdf/page-001.png")
    assert not ignored("QUARANTINE/.gitkeep") and not ignored("CLEAN/.gitkeep")
    tracked = subprocess.run(["git", "ls-files", "QUARANTINE", "CLEAN"], cwd=REPO,
                             capture_output=True, text=True).stdout.split()
    assert sorted(tracked) == ["CLEAN/.gitkeep", "QUARANTINE/.gitkeep"]


def test_agent_permissions_fence_off_quarantine_and_the_web():
    perms = json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]
    deny, allow = perms["deny"], perms["allow"]
    for rule in ("Read(./QUARANTINE/**)", "Edit(./QUARANTINE/**)", "Edit(./tools/**)",
                 "Edit(./.claude/**)", "WebFetch", "WebSearch"):
        assert rule in deny, rule
    assert perms["defaultMode"] == "default"
    assert perms["disableBypassPermissionsMode"] == "disable"
    assert not any("q-shell" in rule or rule in ("Bash", "Bash(*)") for rule in allow)


def test_demo_runs_and_uses_the_real_verdict_wording():
    demo = subprocess.run([str(REPO / "tools" / "demo-inspect.sh")], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)
    assert demo.returncode == 0
    real = (REPO / "tools" / "image" / "q").read_text()
    messages = {line.split(None, 2)[2] for line in demo.stdout.splitlines() if line.startswith("verdict:")}
    assert len(messages) == 3
    for message in messages:
        assert message in real, f"demo wording drifted from tools/image/q: {message!r}"
