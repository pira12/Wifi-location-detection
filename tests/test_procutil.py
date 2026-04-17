from wifipi.procutil import which, missing_tools


def test_which_returns_path_for_existing_tool():
    assert which("sh") is not None


def test_which_returns_none_for_nonexistent():
    assert which("definitely-not-a-real-binary-xyz") is None


def test_missing_tools_filters_existing_and_absent():
    result = missing_tools(["sh", "definitely-not-a-real-binary-xyz"])
    assert result == ["definitely-not-a-real-binary-xyz"]


def test_missing_tools_returns_empty_when_all_present():
    assert missing_tools(["sh"]) == []
