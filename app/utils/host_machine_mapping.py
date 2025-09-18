import re
from typing import Optional


def resolve_host(hostname: Optional[str]) -> str:
    if hostname is None:
        return "unknown"
    if re.search(r"\.frontera\.tacc\.", hostname):
        return "Frontera@TACC"
    elif re.search(r"\.delta\.ncsa\.", hostname):
        return "Delta@NCSA"
    elif re.search(r"\.ls6\.tacc\.", hostname):
        return "Lonestar6@TACC"
    elif re.search(r"\.anvil\.rcac\.purdue\.edu", hostname):
        return "Anvil@RCAC"
    elif re.search(r"\.tacc\.utexas\.edu", hostname):
        return "tacc-system"
    elif re.search(r"\.ncsa\.illinois\.edu", hostname):
        return "ncsa-system"
    else:
        return "unknown"
