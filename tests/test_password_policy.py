import time
import re
import pytest
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationError:
    code: str
    message: str


class ValidationResponse:
    def __init__(self, status_code: int, error: Optional[ValidationError] = None):
        self.status_code = status_code
        self.error = error


def validate_password(password: str) -> ValidationResponse:
    if not password or len(password) < 8:
        return ValidationResponse(
            status_code=400,
            error=ValidationError(code="VALID-001", message="Password must be at least 8 characters long")
        )
    return ValidationResponse(status_code=200, error=None)


class TestPasswordPolicy:

    def test_reject_short_password(self):
        response = validate_password("Ab1!")
        assert response.status_code == 400
        assert response.error is not None
        assert response.error.code == "VALID-001"

    def test_reject_empty_password(self):
        response = validate_password("")
        assert response.status_code == 400
        assert response.error is not None
        assert response.error.code == "VALID-001"

    def test_accept_valid_length_password(self):
        response = validate_password("Abcdef12")
        assert response.status_code == 200
        assert response.error is None

    def test_response_time_within_200ms(self):
        start = time.time()
        validate_password("Ab1!")
        elapsed = (time.time() - start) * 1000
        assert elapsed <= 200, f"Response time {elapsed}ms exceeds 200ms limit"
