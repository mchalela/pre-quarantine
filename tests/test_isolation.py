"""The container really is locked down. These are the properties everything else rests on."""
import json
import os
import subprocess
import time

import pytest

import samples
from conftest import IMAGE, REPO

PROBE = r"""
echo "uid=$(id -u)"
echo "net=$(ls /sys/class/net | tr '\n' ' ')"
echo "caps=$(grep CapEff /proc/self/status | awk '{print $2}')"
echo "nnp=$(grep NoNewPrivs /proc/self/status | awk '{print $2}')"
touch /probe 2>/dev/null && echo "rootfs=writable" || echo "rootfs=readonly"
touch /tmp/probe 2>/dev/null && echo "tmp=writable" || echo "tmp=readonly"
echo "home=$(ls -A /home /root 2>/dev/null | grep -v : | tr -d '\n')"
echo "sock=$(ls /var/run/docker.sock 2>/dev/null)"
echo "swap=$(cat /sys/fs/cgroup/memory.swap.max 2>/dev/null)"
"""


def probe(output: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)


@pytest.fixture(scope="module")
def tools_container() -> dict[str, str]:
    """Run the probe with exactly the flags the scripts use (taken from tools/_lib.sh)."""
    script = f'source "{REPO}/tools/_lib.sh"; docker run -i "${{HARDEN[@]}}" --entrypoint sh {IMAGE} -s'
    result = subprocess.run(["bash", "-c", script], input=PROBE, capture_output=True, text=True, check=True)
    return probe(result.stdout)


def test_tools_container_has_no_network(tools_container):
    assert tools_container["net"].split() == ["lo"]


def test_tools_container_is_not_root_and_matches_the_caller(tools_container):
    assert tools_container["uid"] == str(os.getuid()) != "0"


def test_tools_container_has_no_capabilities_and_cannot_gain_any(tools_container):
    assert int(tools_container["caps"], 16) == 0
    assert tools_container["nnp"] == "1"


def test_tools_container_filesystem_is_read_only_except_tmp(tools_container):
    assert tools_container["rootfs"] == "readonly"
    assert tools_container["tmp"] == "writable"


def test_tools_container_sees_no_home_and_no_docker_socket(tools_container):
    assert tools_container["home"] == ""
    assert tools_container["sock"] == ""


def test_tools_container_gets_no_swap_on_top_of_its_memory_limit(tools_container):
    # Empty where the kernel does not report it (older cgroup layout); "0" where it does.
    assert tools_container["swap"] in ("0", "")


def test_every_run_of_the_tools_has_a_time_limit():
    """The image starts its script under timeout, as process 1: when the time is up, the container ends."""
    entrypoint = json.loads(subprocess.run(["docker", "image", "inspect", "-f", "{{json .Config.Entrypoint}}", IMAGE],
                                           capture_output=True, text=True, check=True).stdout)
    assert entrypoint[:3] == ["timeout", "-s", "KILL"] and int(entrypoint[3]) <= 900
    assert entrypoint[-1] == "/usr/local/bin/q"
    # The same arrangement with a one-second limit, and a script kept waiting for input that never ends.
    stuck = subprocess.Popen(["docker", "run", "--rm", "-i", "--network", "none", "--entrypoint", "timeout", IMAGE,
                              "-s", "KILL", "1", "/usr/local/bin/q", "inspect", "x.pdf"],
                             stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert stuck.wait(timeout=60) == 137
    stuck.stdin.close()


@pytest.mark.parametrize("script", ["q-inspect.sh", "q-convert.sh", "q-extract.sh"])
def test_a_run_that_was_killed_is_reported_as_such_and_leaves_nothing(box, taken_over, script):
    result = box.run(script, box.put("x.pdf", b"killed\n"), env=taken_over)
    assert result.returncode != 0
    assert "time limit" in result.stderr
    assert not any(l.startswith("verdict:") for l in result.stdout.splitlines())
    assert list(box.clean.iterdir()) == [] and box.scratch_left() == []
    assert not (box.quarantine / "sender" / "x.pdf.extracted").exists()


# --- the sandbox shell ---------------------------------------------------------------------

@pytest.fixture
def repo_dir(box):
    folder = box.quarantine / "sender" / "repo"
    folder.mkdir(parents=True)
    (folder / "marker.txt").write_text("here\n")
    return folder


def shell(box, folder, *options: str) -> dict[str, str]:
    result = subprocess.run([str(box.root / "tools" / "q-shell.sh"), str(folder), *options, "--", "sh", "-s"],
                            input=PROBE + 'echo "work=$(ls /work | tr "\\n" " ")"\necho "cwd=$(pwd)"\n',
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr
    return probe(result.stdout)


def test_shell_sees_only_the_chosen_folder_and_has_no_network(box, repo_dir):
    seen = shell(box, repo_dir)
    assert seen["work"].split() == ["marker.txt"] and seen["cwd"] == "/work"
    assert seen["net"].split() == ["lo"]
    assert seen["uid"] == str(os.getuid())
    assert int(seen["caps"], 16) == 0 and seen["nnp"] == "1"
    assert seen["home"] == "" and seen["sock"] == ""


def test_shell_network_is_opt_in_announced_and_kept_apart_from_other_containers(box, repo_dir):
    result = subprocess.run([str(box.root / "tools" / "q-shell.sh"), str(repo_dir), "--net", "--", "ls", "/sys/class/net"],
                            capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr
    assert "eth0" in result.stdout.split()
    assert "NETWORK ON" in result.stderr and "local network" in result.stderr
    # Not docker's default network, and containers on this one cannot talk to each other.
    options = json.loads(subprocess.run(["docker", "network", "inspect", "-f", "{{json .Options}}", "pre-quarantine"],
                                        capture_output=True, text=True, check=True).stdout)
    assert options.get("com.docker.network.bridge.enable_icc") == "false"


def test_shell_refuses_folder_names_that_could_confuse_docker(box):
    odd = box.quarantine / "a:b,c"
    odd.mkdir()
    result = box.run("q-shell.sh", odd, "--", "true")
    assert result.returncode != 0 and "rename the folder" in result.stderr


@pytest.mark.parametrize("value", ["--hostname=changed", "--volume=/:/host", "-v", ""])
def test_shell_image_option_takes_an_image_name_and_nothing_else(box, repo_dir, value):
    """`--image --volume=/:/host -- python:3.12-slim ...` used to hand that option straight to docker."""
    result = box.run("q-shell.sh", repo_dir, "--image", value, "--", "python:3.12-slim", "hostname")
    assert result.returncode != 0 and "not an image name" in result.stderr
    assert "changed" not in result.stdout
    missing = box.run("q-shell.sh", repo_dir, "--image")
    assert missing.returncode != 0 and "--image needs" in missing.stderr


def test_tools_keep_out_of_a_folder_while_a_shell_is_open_on_it(box, repo_dir):
    """Code in the shell could swap a file for a link between a tool's check and its use of the file."""
    inside = repo_dir / "brief.pdf"
    inside.write_bytes(samples.pdf())
    elsewhere = box.put("brief.pdf", samples.pdf(), sender="other")
    label = f"label=pre-quarantine.shell={repo_dir.resolve()}"
    session = subprocess.Popen([str(box.root / "tools" / "q-shell.sh"), str(repo_dir), "--", "sleep", "60"],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if subprocess.run(["docker", "ps", "-q", "--filter", label], capture_output=True, text=True).stdout.strip():
                break
            time.sleep(0.1)
        else:
            pytest.fail("the sandbox shell did not start")
        for script in ("q-inspect.sh", "q-convert.sh", "q-extract.sh"):
            refused = box.run(script, inside)
            assert refused.returncode != 0 and "sandbox shell is open" in refused.stderr, script
        assert box.run("q-inspect.sh", elsewhere).returncode == 0
    finally:
        running = subprocess.run(["docker", "ps", "-q", "--filter", label], capture_output=True, text=True).stdout.split()
        if running:
            subprocess.run(["docker", "kill", *running], capture_output=True)
        session.wait(timeout=30)
    assert box.run("q-inspect.sh", inside).returncode == 0
