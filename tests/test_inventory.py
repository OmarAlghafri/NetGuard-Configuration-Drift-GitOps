import pytest

from netguard.inventory import load_inventory


def _write(tmp_path, text):
    path = tmp_path / "devices.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_merge_into_devices(tmp_path):
    path = _write(
        tmp_path,
        """
defaults:
  username: admin
  password: secret
  device_type: cisco_ios
devices:
  - name: R1
    host: 192.168.56.20
  - name: SW1
    host: 192.168.56.22
    role: switch
""",
    )
    devices = {d.name: d for d in load_inventory(path)}
    assert devices["R1"].username == "admin"
    assert devices["R1"].password == "secret"
    assert devices["R1"].role == "router"
    assert devices["SW1"].role == "switch"


def test_missing_host_raises(tmp_path):
    path = _write(tmp_path, "devices:\n  - name: R1\n")
    with pytest.raises(ValueError):
        load_inventory(path)


def test_empty_inventory_raises(tmp_path):
    path = _write(tmp_path, "devices: []\n")
    with pytest.raises(ValueError):
        load_inventory(path)
