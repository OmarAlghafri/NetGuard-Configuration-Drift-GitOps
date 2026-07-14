import pytest

BASELINE = """\
hostname R1
!
username admin privilege 15 secret 5 $1$abcd$AAAAAAAAAAAAAAAAAAAAA0
!
interface FastEthernet0/0
 description Link to R2
 ip address 10.0.12.1 255.255.255.252
!
router ospf 1
 router-id 1.1.1.1
 network 10.0.12.0 0.0.0.3 area 0
!
access-list 10 permit 192.168.56.0 0.0.0.255
!
line vty 0 4
 access-class 10 in
 transport input ssh
!
end
"""

# Same device after unauthorised changes:
#  - a rogue admin user was added            (critical)
#  - an over-broad OSPF network was added    (critical)
#  - the VTY access-class was removed         (critical)
#  - the R2 link description was changed      (info)
RUNNING_DRIFT = """\
hostname R1
!
username admin privilege 15 secret 5 $1$abcd$AAAAAAAAAAAAAAAAAAAAA0
username backdoor privilege 15 secret 5 $1$zzzz$BBBBBBBBBBBBBBBBBBBBB1
!
interface FastEthernet0/0
 description TEMP DO NOT SHIP
 ip address 10.0.12.1 255.255.255.252
!
router ospf 1
 router-id 1.1.1.1
 network 10.0.12.0 0.0.0.3 area 0
 network 0.0.0.0 255.255.255.255 area 0
!
access-list 10 permit 192.168.56.0 0.0.0.255
!
line vty 0 4
 transport input ssh
!
end
"""


@pytest.fixture
def baseline() -> str:
    return BASELINE


@pytest.fixture
def running_clean() -> str:
    return BASELINE


@pytest.fixture
def running_drift() -> str:
    return RUNNING_DRIFT
