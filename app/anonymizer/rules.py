import re
from datetime import datetime
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    masker: Callable[[str], str]
    priority: int


# -------------------------
# VALIDATION FUNCTIONS
# -------------------------

def is_valid_bank_card(value: str) -> bool:
    """Validate a bank card number using the Luhn algorithm."""
    digits = [int(ch) for ch in value if ch.isdigit()]

    if len(digits) not in range(13, 20):
        return False

    total = 0

    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2

            if digit > 9:
                digit -= 9

        total += digit

    return total % 10 == 0


# -------------------------
# MASKING FUNCTIONS
# -------------------------

def mask_email(value: str) -> str:
    local, domain = value.split("@", 1)

    if len(local) <= 1:
        masked = "*"
    else:
        masked = local[0] + "*" * max(3, len(local) - 1)

    return f"{masked}@{domain}"


def mask_phone(value: str) -> str:
    digit_positions = [
        i for i, ch in enumerate(value) if ch.isdigit()
    ]

    if len(digit_positions) >= 13:
        return value

    if len(digit_positions) < 4:
        return value

    cutoff = set(digit_positions[:-2])

    return "".join(
        "*" if i in cutoff else ch
        for i, ch in enumerate(value)
    )


def mask_passport(value: str) -> str:
    return re.sub(r"\d", "*", value)


def mask_snils(value: str) -> str:
    seen = 0
    result = []

    for ch in reversed(value):
        if ch.isdigit():
            seen += 1
            result.append(ch if seen <= 2 else "*")
        else:
            result.append(ch)

    return "".join(reversed(result))


def mask_inn(value: str) -> str:
    digits = [int(ch) for ch in value]

    def checksum(numbers, weights):
        total = sum(
            digit * weight
            for digit, weight in zip(numbers, weights)
        )
        return (total % 11) % 10

    if len(digits) == 10:
        expected = checksum(
            digits[:9],
            [2, 4, 10, 3, 5, 9, 4, 6, 8],
        )

        if expected != digits[9]:
            return value

    elif len(digits) == 12:
        first_check = checksum(
            digits[:10],
            [7, 2, 4, 10, 3, 5, 9, 4, 6, 8],
        )

        second_check = checksum(
            digits[:11],
            [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8],
        )

        if first_check != digits[10] or second_check != digits[11]:
            return value

    else:
        return value

    return "*" * (len(value) - 2) + value[-2:]


def mask_bank_card(value: str) -> str:
    if not is_valid_bank_card(value):
        return value

    digits_seen = 0
    total_digits = sum(ch.isdigit() for ch in value)
    result = []

    for ch in value:
        if ch.isdigit():
            digits_seen += 1

            if digits_seen <= total_digits - 4:
                result.append("*")
            else:
                result.append(ch)
        else:
            result.append(ch)

    return "".join(result)


def mask_person(value: str) -> str:
    ignored_phrases = {
        "новым годом",
        "доброе утро",
        "днём рождения",
        "днем рождения",
        "проверка redis",
    }

    if value.casefold() in ignored_phrases:
        return value

    def mask_word(match):
        word = match.group(0)
        return word[0] + "*" * (len(word) - 1)

    return re.sub(
        r"[^\W\d_]+",
        mask_word,
        value,
        flags=re.UNICODE,
    )


def mask_address(value: str) -> str:
    return "[АДРЕС]"


def mask_date(value: str) -> str:
    formats = (
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
    )

    for date_format in formats:
        try:
            datetime.strptime(value, date_format)
            return "[ДАТА]"
        except ValueError:
            continue

    return value


# -------------------------
# ANONYMIZATION RULES
# -------------------------

DEFAULT_RULES = [
    Rule(
        "BANK_CARD",
        re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
        mask_bank_card,
        120,
    ),

    Rule(
        "INN",
        re.compile(r"(?<!\d)(?:\d{10}|\d{12})(?!\d)"),
        mask_inn,
        110,
    ),

    Rule(
        "PASSPORT",
        re.compile(r"(?<!\d)\d{4}\s?\d{6}(?!\d)"),
        mask_passport,
        100,
    ),

    Rule(
        "SNILS",
        re.compile(r"(?<!\d)\d{3}-\d{3}-\d{3}-\d{2}(?!\d)"),
        mask_snils,
        95,
    ),

    Rule(
        "EMAIL",
        re.compile(
            r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b"
        ),
        mask_email,
        90,
    ),

    Rule(
        "DATE",
        re.compile(
            r"(?<!\d)(?:"
            r"\d{4}-\d{2}-\d{2}"
            r"|"
            r"\d{2}[./]\d{2}[./]\d{4}"
            r")(?!\d)"
        ),
        mask_date,
        88,
    ),

    Rule(
        "ADDRESS",
        re.compile(
            r"(?<!\w)"
            r"(?:(?:г(?:ород)?\.?\s*)"
            r"[А-ЯЁA-Z][а-яёa-z-]*"
            r"(?:\s+[А-ЯЁA-Z][а-яёa-z-]*)?"
            r"\s*,?\s*)?"
            r"(?:ул(?:ица)?\.?|пр-т|проспект|"
            r"пер(?:еулок)?\.?|ш(?:оссе)?\.?|"
            r"наб(?:ережная)?\.?|б-р|бул(?:ьвар)?\.?)"
            r"\s*[А-ЯЁA-Z][а-яёa-z-]*"
            r"(?:\s+[А-ЯЁA-Z][а-яёa-z-]*){0,3}"
            r"\s*,?\s*"
            r"(?:д(?:ом)?\.?)\s*\d+[А-Яа-яA-Za-z]?"
            r"(?:\s*,?\s*(?:кв(?:артира)?\.?)\s*\d+)?"
            r"(?!\w)",
            re.IGNORECASE,
        ),
        mask_address,
        85,
    ),

    Rule(
        "PERSON",
        re.compile(
            r"(?<!\w)(?:[А-ЯЁ][а-яё]+|[A-Z][a-z]+)"
            r"(?:\s+(?:[А-ЯЁ][а-яё]+|[A-Z][a-z]+)){1,2}(?!\w)"
        ),
        mask_person,
        70,
    ),

    Rule(
        "PHONE",
        re.compile(r"(?<!\w)\+?\d[\d\s()-]{7,}\d(?!\w)"),
        mask_phone,
        50,
    ),
]