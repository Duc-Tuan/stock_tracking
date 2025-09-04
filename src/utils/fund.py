import re

def replace_suffix_with(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0)
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm")
    
def replace_suffix_with_m(sym: str) -> str:
    # Lấy phần chữ cái và số chính (base symbol)
    base = re.match(r"[A-Z]{6}", sym.upper())
    if base:
        return base.group(0) + "m"
    else:
        # Nếu không match (trường hợp đặc biệt) thì fallback
        return sym.rstrip("cm") + "m"