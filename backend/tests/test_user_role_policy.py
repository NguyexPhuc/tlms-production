import pytest
from fastapi import HTTPException

from app.api.routes.users import validate_role_policy


def test_role_policy_accepts_exactly_one_role():
    assert validate_role_policy(["member"]) == ["member"]


@pytest.mark.parametrize(
    "roles",
    [[], ["candidate", "member"], ["mentor", "admin"]],
)
def test_role_policy_rejects_zero_or_multiple_roles(roles):
    with pytest.raises(HTTPException) as exc_info:
        validate_role_policy(roles)

    assert exc_info.value.status_code == 400
    assert "đúng một quyền" in exc_info.value.detail
