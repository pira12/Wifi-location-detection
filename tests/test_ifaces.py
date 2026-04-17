from pathlib import Path

import pytest

from wifipi.ifaces import (
    InterfaceInfo,
    InterfaceManager,
    Role,
    parse_iw_dev,
)

FIXT = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXT / name).read_text()


def test_parse_empty():
    assert parse_iw_dev(_read("iw_dev_empty.txt")) == []


def test_parse_single_adapter():
    ifaces = parse_iw_dev(_read("iw_dev_single.txt"))
    assert ifaces == [InterfaceInfo(name="wlan0", mode="managed", phy="phy#0")]


def test_parse_dual_adapter():
    ifaces = {i.name: i for i in parse_iw_dev(_read("iw_dev_dual.txt"))}
    assert ifaces["wlan1mon"].mode == "monitor"
    assert ifaces["wlan2"].mode == "managed"
    assert ifaces["wlan0"].mode == "managed"
    assert ifaces["wlan1mon"].phy == "phy#1"


def test_manager_assign_and_lookup():
    mgr = InterfaceManager()
    mgr.assign(Role.MON, "wlan1mon")
    mgr.assign(Role.AP, "wlan2")
    assert mgr.get(Role.MON) == "wlan1mon"
    assert mgr.get(Role.AP) == "wlan2"
    assert mgr.get(Role.ATTACK) is None


def test_manager_clear():
    mgr = InterfaceManager()
    mgr.assign(Role.MON, "wlan1mon")
    mgr.clear()
    assert mgr.get(Role.MON) is None


def test_manager_rename_updates_role():
    """After airmon-ng renames wlan1 → wlan1mon, we update the role in place."""
    mgr = InterfaceManager()
    mgr.assign(Role.MON, "wlan1")
    mgr.rename(old="wlan1", new="wlan1mon")
    assert mgr.get(Role.MON) == "wlan1mon"


def test_role_from_string_accepts_aliases():
    assert Role.from_str("mon") is Role.MON
    assert Role.from_str("monitor") is Role.MON
    assert Role.from_str("attack") is Role.ATTACK
    assert Role.from_str("ap") is Role.AP
    with pytest.raises(ValueError):
        Role.from_str("bogus")
