"""
Brazilian CPF / CNPJ validators — ports of the NestJS helpers at
api/src/modules/users/common/utils/validate{Cpf,Cnpj}.ts so the behavior
matches exactly.
"""
from __future__ import annotations

import re


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def validate_cpf(cpf: str) -> bool:
    clean = _digits(cpf)
    if len(clean) != 11:
        return False
    if len(set(clean)) == 1:  # all same digits
        return False

    total = sum(int(clean[i]) * (10 - i) for i in range(9))
    remainder = (total * 10) % 11
    if remainder in (10, 11):
        remainder = 0
    if remainder != int(clean[9]):
        return False

    total = sum(int(clean[i]) * (11 - i) for i in range(10))
    remainder = (total * 10) % 11
    if remainder in (10, 11):
        remainder = 0
    if remainder != int(clean[10]):
        return False
    return True


def validate_cnpj(cnpj: str) -> bool:
    clean = _digits(cnpj)
    if len(clean) != 14:
        return False
    if len(set(clean)) == 1:
        return False

    weight = 2
    total = 0
    for i in range(11, -1, -1):
        total += int(clean[i]) * weight
        weight = 2 if weight == 9 else weight + 1
    remainder = total % 11
    first = 0 if remainder < 2 else 11 - remainder
    if first != int(clean[12]):
        return False

    weight = 2
    total = 0
    for i in range(12, -1, -1):
        total += int(clean[i]) * weight
        weight = 2 if weight == 9 else weight + 1
    remainder = total % 11
    second = 0 if remainder < 2 else 11 - remainder
    if second != int(clean[13]):
        return False
    return True


PHONE_DIGITS_OK = {10, 11}


def validate_phone_digits(phone: str) -> bool:
    """Brazilian phone: 10 or 11 digits after stripping non-digits."""
    return len(_digits(phone)) in PHONE_DIGITS_OK


def strip_non_digits(value: str) -> str:
    return _digits(value)
