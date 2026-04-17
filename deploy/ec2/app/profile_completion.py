"""
Profile completion calculator — port of
`UsersService.getProfileCompletionStatus` in the NestJS backend.

9 total fields: name, email, phone, cpf, role (not MEMBER), plus 4 profile
fields (city, interestSectors, interestRegion, investmentRange).
"""
from __future__ import annotations

from typing import Any

from app.models import User


def compute_completion(user: User) -> dict[str, Any]:
    missing: list[str] = []
    completed = 0
    TOTAL = 9

    if user.name:
        completed += 1
    else:
        missing.append("name")

    if user.email:
        completed += 1
    else:
        missing.append("email")

    if user.phone:
        completed += 1
    else:
        missing.append("phone")

    if user.cpf:
        completed += 1
    else:
        missing.append("cpf")

    if user.role and user.role != "MEMBER":
        completed += 1
    else:
        missing.append("role")

    profile = getattr(user, "profile", None)
    if profile is not None:
        if profile.city:
            completed += 1
        else:
            missing.append("city")
        if profile.interestSectors:
            completed += 1
        else:
            missing.append("interestSectors")
        if profile.interestRegion:
            completed += 1
        else:
            missing.append("interestRegion")
        if profile.investmentRange:
            completed += 1
        else:
            missing.append("investmentRange")
    else:
        missing.extend(
            ["city", "interestSectors", "interestRegion", "investmentRange"]
        )

    percentage = round((completed / TOTAL) * 100)
    return {
        "isComplete": len(missing) == 0,
        "completionPercentage": percentage,
        "missingFields": missing,
    }
