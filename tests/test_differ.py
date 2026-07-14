from netguard.differ import diff_configs


def test_identical_configs_have_no_drift(baseline, running_clean):
    result = diff_configs("R1", baseline, running_clean)
    assert not result.has_drift
    assert result.changes == []


def test_added_line_is_reported_as_addition(baseline, running_drift):
    result = diff_configs("R1", baseline, running_drift)
    added = [c.line for c in result.changes if c.op == "+"]
    assert any("username backdoor" in line for line in added)
    assert any("network 0.0.0.0 255.255.255.255 area 0" in line for line in added)


def test_removed_line_is_reported_as_removal(baseline, running_drift):
    result = diff_configs("R1", baseline, running_drift)
    removed = [c.line for c in result.changes if c.op == "-"]
    assert any("access-class 10 in" in line for line in removed)


def test_child_change_carries_parent(baseline, running_drift):
    result = diff_configs("R1", baseline, running_drift)
    desc = [c for c in result.changes if "DO NOT SHIP" in c.line]
    assert desc, "expected the changed interface description to be detected"
    assert desc[0].parent == "interface FastEthernet0/0"
