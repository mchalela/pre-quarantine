from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
IMAGE = "quarantine-tools"


@pytest.fixture(scope="session", autouse=True)
def image() -> str:
    """The tools image must exist. Build it once if it does not."""
    if shutil.which("docker") is None:
        pytest.exit("docker is required to run these tests", returncode=2)
    found = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    if found.returncode != 0:
        subprocess.run([str(REPO / "tools" / "build.sh")], check=True)
    return IMAGE


@dataclass
class Box:
    """A private copy of the tools with its own QUARANTINE/ and CLEAN/, so tests
    never touch the real folders."""
    root: Path

    @property
    def quarantine(self) -> Path:
        return self.root / "QUARANTINE"

    @property
    def clean(self) -> Path:
        return self.root / "CLEAN"

    def put(self, name: str, data: bytes, sender: str = "sender") -> Path:
        folder = self.quarantine / sender
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(data)
        return path

    def run(self, script: str, *args: str | os.PathLike, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(self.root / "tools" / script), *map(str, args)],
            cwd=self.root, capture_output=True, text=True, timeout=300,
            stdin=subprocess.DEVNULL, env={**os.environ, "NO_COLOR": "1", **(env or {})},
        )

    def inspect(self, path: Path) -> "Inspection":
        result = self.run("q-inspect.sh", path)
        assert result.returncode == 0, result.stderr + result.stdout
        return Inspection(result.stdout)


@dataclass
class Inspection:
    out: str

    def _field(self, key: str) -> str:
        lines = [l for l in self.out.splitlines() if l.startswith(key)]
        assert len(lines) == 1, f"expected one {key!r} line in:\n{self.out}"
        return lines[0][len(key):].strip()

    @property
    def verdict(self) -> str:
        return self._field("verdict:").split()[0]

    @property
    def next(self) -> str:
        return self._field("next:")


@pytest.fixture
def box(tmp_path: Path) -> Box:
    root = tmp_path / "box"
    shutil.copytree(REPO / "tools", root / "tools")
    (root / "QUARANTINE").mkdir()
    (root / "CLEAN").mkdir()
    return Box(root)
