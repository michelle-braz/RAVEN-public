"""
Unit tests for AnalyzeRequest input validation.

All validation is enforced by a Pydantic field_validator; FastAPI automatically
converts ValidationError → HTTP 422, so model-level tests are sufficient.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from raven.api.v1.router import AnalyzeRequest


def test_empty_message_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(message="")


def test_whitespace_only_message_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(message="   ")


def test_missing_message_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate({"source": "unknown"})


def test_numeric_message_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate({"message": 123, "source": "unknown"})


def test_message_with_surrounding_whitespace_is_normalized() -> None:
    req = AnalyzeRequest(message="  unauthorized login failure  ")
    assert req.message == "unauthorized login failure"


def test_valid_message_accepted() -> None:
    req = AnalyzeRequest(message="user login successful from known device")
    assert req.message == "user login successful from known device"
