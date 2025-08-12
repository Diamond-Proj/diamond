import re


def resolve_host(hostname: str) -> str:
    if re.search(r"\.frontera\.tacc\.", hostname):
        return "tacc-frontera"
    elif re.search(r"\.delta\.ncsa\.", hostname):
        return "ncsa-delta"
    elif re.search(r"\.ls6\.tacc\.", hostname):
        return "tacc-lonestar6"
    elif re.search(r"\.tacc\.utexas\.edu", hostname):
        return "tacc-system"
    elif re.search(r"\.ncsa\.illinois\.edu", hostname):
        return "ncsa-system"
    else:
        return "unknown"
