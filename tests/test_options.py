import pytest

from wifipi.options import OptionSpec, OptionStore, ResolvedOption


def test_local_overrides_global():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    store.set_global("CHANNEL", "6")
    store.set_local("CHANNEL", "11")
    resolved = store.resolve("CHANNEL")
    assert resolved == ResolvedOption(value="11", source="local")


def test_global_used_when_no_local():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    store.set_global("CHANNEL", "6")
    assert store.resolve("CHANNEL") == ResolvedOption(value="6", source="global")


def test_default_used_when_nothing_set():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    assert store.resolve("CHANNEL") == ResolvedOption(value="1", source="default")


def test_required_missing_is_none():
    store = OptionStore(specs={"BSSID": OptionSpec(required=True, default=None)})
    assert store.resolve("BSSID") is None


def test_missing_required_lists_gaps():
    store = OptionStore(specs={
        "BSSID": OptionSpec(required=True, default=None),
        "CLIENT": OptionSpec(required=True, default=None),
        "CHANNEL": OptionSpec(required=True, default=None),
    })
    store.set_global("BSSID", "AA:BB:CC:11:22:33")
    missing = store.missing_required()
    assert set(missing) == {"CLIENT", "CHANNEL"}


def test_unset_local_reveals_global():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    store.set_global("CHANNEL", "6")
    store.set_local("CHANNEL", "11")
    store.unset_local("CHANNEL")
    assert store.resolve("CHANNEL") == ResolvedOption(value="6", source="global")


def test_reject_unknown_key_on_local_set():
    store = OptionStore(specs={"CHANNEL": OptionSpec(required=False, default="1")})
    with pytest.raises(KeyError):
        store.set_local("NOPE", "x")


def test_global_accepts_unknown_keys():
    """Globals are session-wide; set before a module is loaded."""
    store = OptionStore(specs={})
    store.set_global("BSSID", "AA:BB:CC:11:22:33")
    # Resolving an unknown key with only a global value still works.
    assert store.resolve("BSSID") == ResolvedOption(value="AA:BB:CC:11:22:33", source="global")
