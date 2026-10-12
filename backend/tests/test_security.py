import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request

from app import main
from app.config import settings
from app.models.schemas import AnalyzeRequest, ReportRequest


def _request(peer: str) -> Request:
    return Request({"type": "http", "method": "POST", "path": "/api/analyze", "headers": [], "client": (peer, 12345), "server": ("test", 8000), "scheme": "http", "query_string": b""})


def test_analysis_inputs_are_trimmed_and_bounded():
    request = AnalyzeRequest(company1="  HAL  ", company2="Mazagon Dock")
    assert request.get_company_a() == "HAL"

    with pytest.raises(ValidationError):
        AnalyzeRequest(company1="H" * 121, company2="HAL")
    with pytest.raises(ValidationError):
        AnalyzeRequest(company1="HAL\nInjected log line", company2="HAL")


def test_report_labels_reject_controls_and_are_bounded():
    with pytest.raises(ValidationError):
        ReportRequest(company1="HAL", company2="VBL", student_name="Student\nInjected")
    with pytest.raises(ValidationError):
        ReportRequest(company1="HAL", company2="VBL", roll_number="R" * 41)


def test_cors_is_explicit_and_credential_free():
    cors = next(middleware for middleware in main.app.user_middleware if middleware.cls.__name__ == "CORSMiddleware")
    assert "*" not in cors.kwargs["allow_origins"]
    assert cors.kwargs["allow_credentials"] is False
    assert set(cors.kwargs["allow_methods"]) == {"GET", "POST"}


def test_analysis_rate_limit_returns_retry_after(monkeypatch):
    monkeypatch.setattr(settings, "ANALYZE_RATE_LIMIT_PER_MINUTE", 2)
    main._ANALYZE_REQUESTS.clear()
    peer = "192.0.2.44"
    main.enforce_analyze_rate_limit(_request(peer))
    main.enforce_analyze_rate_limit(_request(peer))

    with pytest.raises(HTTPException) as raised:
        main.enforce_analyze_rate_limit(_request(peer))

    assert raised.value.status_code == 429
    assert int(raised.value.headers["Retry-After"]) > 0
    main._ANALYZE_REQUESTS.clear()
