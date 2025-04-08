import re

def resolve_host(hostname: str) -> str:
    if re.search(r'\.frontera\.tacc\.', hostname):
        return "tacc-frontera"
    elif re.search(r'\.delta\.ncsa\.', hostname):
        return "ncsa-delta" 
    else:
        return "unknown"
