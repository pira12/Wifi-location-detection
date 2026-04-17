from pathlib import Path

from wifipi.loot import LootManager


def test_run_dir_creates_timestamped_subdir(tmp_path):
    mgr = LootManager(root=tmp_path)
    run = mgr.new_run("handshakes", "my-module")
    assert run.exists()
    assert run.parent == tmp_path / "handshakes"
    assert "my-module" in run.name
    # timestamp prefix: 2026-04-17_18-30-12-my-module
    assert run.name[:4].isdigit()


def test_recent_lists_most_recent_first(tmp_path):
    mgr = LootManager(root=tmp_path)
    a = mgr.new_run("scans", "scan-a")
    b = mgr.new_run("scans", "scan-b")
    c = mgr.new_run("handshakes", "hs")
    recent = mgr.recent(limit=10)
    names = [r.name for r in recent]
    assert names[0] == c.name    # newest first (insertion order works since we just made them)
    assert set(names) == {a.name, b.name, c.name}


def test_recent_filter_by_category(tmp_path):
    mgr = LootManager(root=tmp_path)
    mgr.new_run("scans", "a")
    mgr.new_run("handshakes", "b")
    mgr.new_run("scans", "c")
    runs = mgr.recent(category="scans", limit=10)
    assert len(runs) == 2
    assert all(r.parent.name == "scans" for r in runs)


def test_clean_removes_all(tmp_path):
    mgr = LootManager(root=tmp_path)
    mgr.new_run("scans", "x")
    mgr.clean()
    assert not any(tmp_path.iterdir())
