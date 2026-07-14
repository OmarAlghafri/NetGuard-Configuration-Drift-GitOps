import pytest

from netguard.classifier import Classifier, Severity
from netguard.differ import diff_configs


@pytest.fixture
def classifier():
    return Classifier()


@pytest.mark.parametrize(
    "line,expected",
    [
        ("router ospf 1", Severity.CRITICAL),
        (" network 0.0.0.0 255.255.255.255 area 0", Severity.CRITICAL),
        (" access-class 10 in", Severity.CRITICAL),
        ("username backdoor privilege 15 secret 5 x", Severity.CRITICAL),
        ("enable secret 5 x", Severity.CRITICAL),
        ("vlan 999", Severity.WARNING),
        (" switchport access vlan 20", Severity.WARNING),
        (" ip address 10.0.0.1 255.255.255.0", Severity.WARNING),
        (" description anything", Severity.INFO),
        (" banner motd test", Severity.INFO),
    ],
)
def test_line_classification(classifier, line, expected):
    severity, _ = classifier.classify_line(line)
    assert severity == expected


def test_classify_result_returns_highest_severity(classifier, baseline, running_drift):
    result = diff_configs("R1", baseline, running_drift)
    assert classifier.classify(result) == Severity.CRITICAL
    # every change is annotated after classify()
    assert all(change.severity for change in result.changes)


def test_clean_result_is_info(classifier, baseline, running_clean):
    result = diff_configs("R1", baseline, running_clean)
    assert classifier.classify(result) == Severity.INFO
