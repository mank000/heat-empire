import re


def format_phone(value):
    if not re.fullmatch(r"\+?[0-9 .()\-–—\u00a0\u202f]+", value):
        return value

    digits = re.sub(r"[^0-9]", "", value)
    has_plus = value.startswith("+")
    if len(digits) == 11 and (digits[0] == "7" or (digits[0] == "8" and not has_plus)):
        digits = digits[1:]
    elif len(digits) != 10 or has_plus:
        return value

    return f"+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}"
