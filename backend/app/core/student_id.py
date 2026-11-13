"""Validation helpers for LHU student identifiers."""
import re
from typing import Optional


STUDENT_ID_PATTERN = re.compile(r"^\d{9}$")


def is_valid_student_id(value: Optional[str]) -> bool:
    """Return whether value is exactly nine decimal digits."""
    return bool(STUDENT_ID_PATTERN.fullmatch((value or "").strip()))


def normalize_student_id(value: str) -> str:
    """Normalize and validate a student ID for storage and LHU requests."""
    normalized = value.strip()
    if not is_valid_student_id(normalized):
        raise ValueError("MSSV phải gồm đúng 9 chữ số")
    return normalized
