import pytest
from pydantic import ValidationError

from app.api.routes.users import StudentIdUpdate
from app.core.student_id import is_valid_student_id, normalize_student_id
from app.services.background_tasks import _is_syncable_student_id


@pytest.mark.parametrize("value", ["123456789", "000000001"])
def test_student_id_accepts_exactly_nine_digits(value):
    assert is_valid_student_id(value)
    assert normalize_student_id(f" {value} ") == value
    assert StudentIdUpdate(student_id=value).student_id == value
    assert _is_syncable_student_id(value)


@pytest.mark.parametrize(
    "value",
    ["12345678", "1234567890", "12345ABCD", "TLMS00001", ""],
)
def test_student_id_rejects_non_nine_digit_values(value):
    assert not is_valid_student_id(value)
    assert not _is_syncable_student_id(value)
    with pytest.raises(ValueError):
        normalize_student_id(value)
    with pytest.raises(ValidationError):
        StudentIdUpdate(student_id=value)
