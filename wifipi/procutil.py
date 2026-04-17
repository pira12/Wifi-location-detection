"""Thin wrappers around subprocess for the console.

Exposes:
- which(tool) -> str | None        : shutil.which, isolated for mocking.
- missing_tools(names) -> list[str]: names absent from PATH.
- run(argv, **kw) -> CompletedProcess: foreground blocking call.
- popen(argv, log_path) -> Popen    : background, stdout+stderr → log_path.
- terminate(proc, timeout=3.0) -> int: SIGTERM, then SIGKILL if needed.
"""

from __future__ import annotations

import shutil
import signal
import subprocess
from pathlib import Path


def which(tool: str) -> str | None:
    return shutil.which(tool)


def missing_tools(names: list[str]) -> list[str]:
    return [n for n in names if which(n) is None]


def run(argv: list[str], *, check: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Foreground blocking subprocess call. Caller decides stdout/stderr."""
    return subprocess.run(argv, check=check, **kwargs)


def popen(argv: list[str], log_path: Path) -> subprocess.Popen:
    """Background process whose combined stdout/stderr is appended to log_path."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(log_path, "ab", buffering=0)
    return subprocess.Popen(
        argv,
        stdout=fh,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def terminate(proc: subprocess.Popen, timeout: float = 3.0) -> int:
    """SIGTERM then SIGKILL. Returns the process's final returncode."""
    if proc.poll() is not None:
        return proc.returncode
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    return proc.returncode
