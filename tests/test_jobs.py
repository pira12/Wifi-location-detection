import time
from pathlib import Path

import pytest

from wifipi.jobs import JobManager, JobState


def test_start_and_kill(tmp_path):
    mgr = JobManager()
    job = mgr.start(
        name="sleep-test",
        argv=["sleep", "30"],
        log_path=tmp_path / "sleep.log",
    )
    assert job.state is JobState.RUNNING
    assert len(mgr.list()) == 1
    mgr.kill(job.id)
    # Give the JobManager's watcher thread a moment to flip state.
    for _ in range(20):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert mgr.get(job.id).state is JobState.KILLED


def test_natural_finish(tmp_path):
    mgr = JobManager()
    job = mgr.start(
        name="true-test",
        argv=["sh", "-c", "exit 0"],
        log_path=tmp_path / "true.log",
    )
    for _ in range(40):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert mgr.get(job.id).state is JobState.FINISHED


def test_ids_increment():
    mgr = JobManager()
    a = mgr.start(name="a", argv=["sleep", "30"], log_path=Path("/dev/null"))
    b = mgr.start(name="b", argv=["sleep", "30"], log_path=Path("/dev/null"))
    assert a.id == 0
    assert b.id == 1
    mgr.kill_all()


def test_log_file_receives_output(tmp_path):
    mgr = JobManager()
    log = tmp_path / "echo.log"
    job = mgr.start(name="echo", argv=["sh", "-c", "echo hello"], log_path=log)
    for _ in range(40):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert "hello" in log.read_text()


def test_finish_callback_invoked(tmp_path):
    calls = []

    def cb(job):
        calls.append((job.id, job.name, job.state))

    mgr = JobManager(on_finish=cb)
    job = mgr.start(name="cb", argv=["sh", "-c", "exit 3"], log_path=tmp_path / "cb.log")
    for _ in range(40):
        if mgr.get(job.id).state is not JobState.RUNNING:
            break
        time.sleep(0.05)
    assert calls and calls[0][0] == job.id
    # exit 3 → FAILED (non-zero exit, not killed by us)
    assert calls[0][2] is JobState.FAILED


def test_running_count():
    mgr = JobManager()
    j = mgr.start(name="s", argv=["sleep", "30"], log_path=Path("/dev/null"))
    assert mgr.running_count() == 1
    mgr.kill(j.id)
    mgr.kill_all()
