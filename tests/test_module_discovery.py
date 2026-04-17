from wifipi.console import discover_modules


def test_discover_returns_list():
    mods = discover_modules()
    assert isinstance(mods, list)


def test_every_module_has_name_and_category():
    for mod in discover_modules():
        assert mod.NAME, f"{mod.__name__} missing NAME"
        assert mod.CATEGORY in {"recon", "attack", "post", "util"}, \
            f"{mod.NAME} has invalid category {mod.CATEGORY!r}"
