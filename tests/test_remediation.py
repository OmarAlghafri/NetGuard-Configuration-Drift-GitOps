from netguard.classifier import Classifier
from netguard.differ import diff_configs
from netguard.remediation import build_revert_commands


def test_added_global_line_is_negated(baseline, running_drift):
    result = diff_configs("R1", baseline, running_drift)
    commands = build_revert_commands(result)
    assert any(c.startswith("no username backdoor") for c in commands)


def test_removed_line_is_reapplied(baseline, running_drift):
    result = diff_configs("R1", baseline, running_drift)
    commands = build_revert_commands(result)
    assert any("access-class 10 in" in c and not c.strip().startswith("no") for c in commands)


def test_addition_negated_before_removal_reapplied(baseline, running_drift):
    # The interface description changed (a removal paired with an addition).
    # The drifted value must be negated before the baseline value is re-applied,
    # otherwise the negation would wipe out the value just restored.
    result = diff_configs("R1", baseline, running_drift)
    commands = build_revert_commands(result)
    negate = next(i for i, c in enumerate(commands) if "no description TEMP DO NOT SHIP" in c)
    reapply = next(i for i, c in enumerate(commands) if c.strip() == "description Link to R2")
    assert negate < reapply


def test_child_change_is_wrapped_in_parent_block(baseline, running_drift):
    result = diff_configs("R1", baseline, running_drift)
    Classifier().classify(result)
    commands = build_revert_commands(result)
    # entering the interface must precede its indented corrective line
    assert "interface FastEthernet0/0" in commands
    idx = commands.index("interface FastEthernet0/0")
    assert any(cmd.startswith(" ") for cmd in commands[idx + 1:])
