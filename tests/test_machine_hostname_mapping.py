import pytest

from diamond_backend.app.utils.host_machine_mapping import KNOWN_MACHINES, resolve_host


@pytest.mark.parametrize(
    "hostname, expected",
    [
        ("login.delta.ncsa.illinois.edu", "Delta@NCSA"),
        ("login00.anvil.rcac.purdue.edu", "Anvil@RCAC"),
        ("dtai-login.delta.ncsa.illinois.edu", "Delta@NCSA"),
        ("login2.vista.tacc.utexas.edu", "System@TACC"),
        ("foo.bar", "unknown"),
    ],
)
def test_resolve_host(hostname: str, expected: str):
    assert resolve_host(hostname) == expected, (
        f"{hostname} did not resolve to {expected}"
    )


def ensure_machine_naming_stype():
    "Machine name should be of the form <MachineName>@<Facility>"
    for _pattern, machine in KNOWN_MACHINES:
        assert len(machine.split("@")) == 2
