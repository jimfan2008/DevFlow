import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.testclient import TestClient
from app.core.exceptions import DevFlowException, ProjectNotFoundError, SkillNoAgentError
from app.middleware.error_handler import register_error_handlers


app = FastAPI()
register_error_handlers(app)


@app.get("/test/devflow-error")
def raise_devflow_error():
    raise ProjectNotFoundError("proj-123")


@app.get("/test/skill-error")
def raise_skill_error():
    raise SkillNoAgentError()


@app.get("/test/http-error")
def raise_http_error():
    raise StarletteHTTPException(status_code=404, detail="Not found")


@app.get("/test/validation-error")
def raise_validation_error():
    raise RequestValidationError(errors=[
        {"loc": ("body", "name"), "msg": "field required", "type": "value_error.missing"}
    ])


client = TestClient(app)


class TestErrorHandlerMiddleware:
    def test_devflow_exception_format(self):
        response = client.get("/test/devflow-error")
        assert response.status_code == 404
        body = response.json()
        assert body["code"] == "PROJ_001"
        assert "proj-123" in body["message"]
        assert "details" in body

    def test_skill_exception_format(self):
        response = client.get("/test/skill-error")
        assert response.status_code == 503
        body = response.json()
        assert body["code"] == "SKILL_001"
        assert "details" in body

    def test_http_exception_format(self):
        response = client.get("/test/http-error")
        assert response.status_code == 404
        body = response.json()
        assert body["code"] == "HTTP_404"
        assert body["message"] == "Not found"
        assert "details" in body

    def test_validation_exception_format(self):
        response = client.get("/test/validation-error")
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert "errors" in body["details"]
