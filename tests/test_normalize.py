from netguard.normalize import normalize


def test_drops_volatile_and_blank_lines():
    raw = (
        "Building configuration...\n"
        "Current configuration : 1234 bytes\n"
        "!\n"
        "\n"
        "hostname R1\n"
        "ntp clock-period 17179860\n"
    )
    lines = normalize(raw)
    assert "hostname R1" in lines
    assert "!" in lines
    assert all("Building configuration" not in line for line in lines)
    assert all("Current configuration" not in line for line in lines)
    assert all("clock-period" not in line for line in lines)
    assert "" not in lines


def test_preserves_indentation():
    raw = "interface FastEthernet0/0\n ip address 10.0.12.1 255.255.255.252\n"
    lines = normalize(raw)
    assert lines == ["interface FastEthernet0/0", " ip address 10.0.12.1 255.255.255.252"]
