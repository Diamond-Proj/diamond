import re
from typing import Optional

# Mapping of hostname patterns to human-readable machine names
KNOWN_MACHINES = [
    (r"\.delta\.ncsa\.", "Delta@NCSA"),
    (r"\.frontera\.tacc\.", "Frontera@NCSA"),
    (r"\.ls6\.tacc\.", "Lonestar6@TACC"),
    (r"\.anvil\.rcac\.purdue\.edu", "Anvil@RCAC"),
    (r"\.tacc\.utexas\.edu", "System@TACC"),
    (r"\.ncsa\.illinois\.edu", "System@NCSA"),
]


def resolve_host(hostname: Optional[str]) -> str:
    if hostname is None:
        return "unknown"

    for pattern, machine_name in KNOWN_MACHINES:
        if re.search(pattern, hostname):
            return machine_name

    return "unknown"
