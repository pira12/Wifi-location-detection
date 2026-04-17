"""Background job manager: threads + subprocess.Popen lifecycle.

Each job runs in a watcher thread that waits on the subprocess and updates
the job's state on exit. Lightweight — no event loop required.
"""

from __future__ import annotations

import enum
import itertools
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import procutil


class JobState(enum.Enum):
    RUNNING = "running"
    FINISHED = "finished"   # exited cleanly (returncode 0)
    FAILED = "failed"       # non-zero exit on its own
    KILLED = "killed"       # terminated by us


@dataclass
class Job:
    id: int
    name: str
    started_at: float
    log_path: Path
    proc: subprocess.Popen
    state: JobState = JobState.RUNNING
    returncode: int | None = None
    ended_at: float | None = None

    @property
    def pid(self) -> int:
        return self.proc.pid

    @property
    def elapsed(self) -> float:
        end = self.ended_at if self.ended_at else time.time()
        return end - self.started_at


OnFinish = Callable[[Job], None]


class JobManager:
    def __init__(self, on_finish: OnFinish | None = None):
        self._jobs: dict[int, Job] = {}
        self._lock = threading.Lock()
        self._ids = itertools.count()
        self._on_finish = on_finish

    def start(self, *, name: str, argv: list[str], log_path: Path) -> Job:
        proc = procutil.popen(argv, log_path)
        job = Job(
            id=next(self._ids),
            name=name,
            started_at=time.time(),
            log_path=log_path,
            proc=proc,
        )
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(target=self._watch, args=(job,), daemon=True).start()
        return job

    def _watch(self, job: Job) -> None:
        job.proc.wait()
        job.ended_at = time.time()
        job.returncode = job.proc.returncode
        if job.state is JobState.RUNNING:
            if job.returncode == 0:
                job.state = JobState.FINISHED
            else:
                job.state = JobState.FAILED
        if self._on_finish:
            try:
                self._on_finish(job)
            except Exception:
                pass  # never let a callback break the watcher

    def get(self, job_id: int) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def running(self) -> list[Job]:
        return [j for j in self.list() if j.state is JobState.RUNNING]

    def running_count(self) -> int:
        return len(self.running())

    def kill(self, job_id: int, timeout: float = 3.0) -> bool:
        job = self.get(job_id)
        if job is None or job.state is not JobState.RUNNING:
            return False
        job.state = JobState.KILLED
        procutil.terminate(job.proc, timeout=timeout)
        return True

    def kill_all(self) -> None:
        for j in self.running():
            self.kill(j.id)
