"""The container really is locked down. These are the properties everything else rests on."""
import os
import subprocess

import pytest

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


def test_shell_network_is_opt_in_and_announced(box, repo_dir):
    result = subprocess.run([str(box.root / "tools" / "q-shell.sh"), str(repo_dir), "--net", "--", "ls", "/sys/class/net"],
                            capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr
    assert "eth0" in result.stdout.split()
    assert "NETWORK ON" in result.stderr


def test_shell_refuses_folder_names_that_could_confuse_docker(box):
    odd = box.quarantine / "a:b,c"
    odd.mkdir()
    result = box.run("q-shell.sh", odd, "--", "true")
    assert result.returncode != 0 and "rename the folder" in result.stderr
