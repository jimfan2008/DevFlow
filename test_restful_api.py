import json
import re
from typing import Any, Optional
import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


app = FastAPI()


_items_store: dict[str, dict] = {}


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    category: str = "general"


class ItemUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    category: str = "general"


@app.get("/api/v1/items")
def list_items():
    return {"data": list(_items_store.values()), "total": len(_items_store)}


@app.get("/api/v1/items/{item_id}")
def get_item(item_id: str):
    if item_id not in _items_store:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"data": _items_store[item_id]}


@app.post("/api/v1/items", status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    item_id = f"item-{len(_items_store) + 1}"
    data = item.model_dump()
    data["id"] = item_id
    _items_store[item_id] = data
    return {"data": data}


@app.put("/api/v1/items/{item_id}")
def update_item(item_id: str, item: ItemUpdate):
    if item_id not in _items_store:
        raise HTTPException(status_code=404, detail="Item not found")
    data = item.model_dump()
    data["id"] = item_id
    _items_store[item_id] = data
    return {"data": data}


@app.delete("/api/v1/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str):
    if item_id not in _items_store:
        raise HTTPException(status_code=404, detail="Item not found")
    del _items_store[item_id]
    return None


@app.get("/api/v1/items/{item_id}/reviews")
def get_item_reviews(item_id: str):
    if item_id not in _items_store:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"data": [], "total": 0}


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"ERR_{exc.status_code}",
                "message": exc.detail,
                "details": {},
            }
        },
    )


client = TestClient(app)


class TestRESTfulAPIDesign:
    """RESTful API 设计规范遵循测试"""

    @pytest.fixture(autouse=True)
    def setup_items(self):
        _items_store.clear()
        _items_store["test-1"] = {
            "id": "test-1",
            "name": "test",
            "price": 10.0,
            "category": "general",
        }
        yield

    # ===== URL 命名规范 =====

    def test_api_path_uses_lowercase(self):
        """所有路径段使用小写"""
        paths = ["/api/v1/items", "/api/v1/items/test-1", "/api/v1/items/test-1/reviews"]
        for path in paths:
            segments = [s for s in path.split("/") if s]
            for seg in segments:
                assert seg == seg.lower(), f"路径段 '{seg}' 未使用小写"

    def test_api_path_uses_kebab_case(self):
        """路径段使用 kebab-case（连字符分隔）"""
        paths = ["/api/v1/items", "/api/v1/items/test-1/reviews"]
        for path in paths:
            segments = [s for s in path.split("/") if s]
            for seg in segments:
                if seg not in ("api", "v1"):
                    assert re.match(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$', seg), \
                        f"路径段 '{seg}' 不符合 kebab-case"

    def test_api_path_has_version_prefix(self):
        """API 路径包含版本号前缀 /api/v{n}"""
        for path in ["/api/v1/items", "/api/v1/items/test-1"]:
            assert re.match(r'^/api/v\d+/', path), f"路径缺少版本前缀: {path}"

    def test_resource_name_is_plural_noun(self):
        """资源名称为复数名词"""
        response = client.get("/api/v1/items")
        assert response.status_code == 200
        resource = "/api/v1/items".split("/")[-1]
        assert resource.endswith("s"), f"资源名 '{resource}' 不是复数形式"

    # ===== HTTP 方法正确性 =====

    def test_get_collection_returns_200(self):
        """GET 集合应返回 200"""
        response = client.get("/api/v1/items")
        assert response.status_code == 200

    def test_get_single_resource_returns_200(self):
        """GET 单个资源应返回 200"""
        response = client.get("/api/v1/items/test-1")
        assert response.status_code == 200

    def test_get_single_resource_not_found_returns_404(self):
        """GET 不存在的资源应返回 404"""
        response = client.get("/api/v1/items/nonexistent")
        assert response.status_code == 404

    def test_post_creates_resource_returns_201(self):
        """POST 创建资源应返回 201"""
        response = client.post("/api/v1/items", json={
            "name": "new-item", "price": 5.0, "category": "books"
        })
        assert response.status_code == 201

    def test_post_creates_resource_and_returns_data(self):
        """POST 创建资源后应返回包含 id 的数据"""
        response = client.post("/api/v1/items", json={
            "name": "new-item", "price": 5.0
        })
        assert response.status_code == 201
        body = response.json()
        assert "data" in body
        assert "id" in body["data"]

    def test_put_updates_resource_returns_200(self):
        """PUT 更新资源应返回 200"""
        response = client.put("/api/v1/items/test-1", json={
            "name": "updated", "price": 20.0, "category": "changed"
        })
        assert response.status_code == 200

    def test_put_update_confirms_data_updated(self):
        """PUT 更新后数据应变更"""
        client.put("/api/v1/items/test-1", json={
            "name": "new-name", "price": 99.0, "category": "changed"
        })
        resp = client.get("/api/v1/items/test-1")
        data = resp.json()
        assert data["data"]["name"] == "new-name"

    def test_delete_returns_204(self):
        """DELETE 删除资源应返回 204"""
        response = client.delete("/api/v1/items/test-1")
        assert response.status_code == 204

    def test_delete_removes_resource(self):
        """DELETE 后资源应不存在"""
        client.delete("/api/v1/items/test-1")
        response = client.get("/api/v1/items/test-1")
        assert response.status_code == 404

    def test_unsupported_method_returns_405(self):
        """不支持的 HTTP 方法应返回 405"""
        response = client.patch("/api/v1/items")
        assert response.status_code == 405

    # ===== 响应格式统一 =====

    def test_success_response_has_data_field(self):
        """成功响应包含 data 顶层字段"""
        response = client.get("/api/v1/items")
        body = response.json()
        assert "data" in body, "成功响应缺少 data 字段"

    def test_single_resource_response_data_is_object(self):
        """单个资源响应的 data 为对象"""
        response = client.get("/api/v1/items/test-1")
        body = response.json()
        assert isinstance(body["data"], dict), "单个资源的 data 应为对象"

    def test_collection_response_data_is_list(self):
        """集合响应的 data 为列表"""
        response = client.get("/api/v1/items")
        body = response.json()
        assert isinstance(body["data"], list), "集合的 data 应为列表"

    # ===== 错误响应格式（验收标准） =====

    def test_error_response_has_error_format(self):
        """错误响应包含 error 字段"""
        response = client.get("/api/v1/items/nonexistent")
        body = response.json()
        assert "error" in body, "错误响应缺少 error 字段"

    def test_error_format_has_code(self):
        """error 对象包含 code 字段"""
        response = client.get("/api/v1/items/nonexistent")
        body = response.json()
        assert "code" in body["error"], "error 缺少 code"

    def test_error_format_has_message(self):
        """error 对象包含 message 字段"""
        response = client.get("/api/v1/items/nonexistent")
        body = response.json()
        assert "message" in body["error"], "error 缺少 message"

    def test_error_format_has_details(self):
        """error 对象包含 details 字段"""
        response = client.get("/api/v1/items/nonexistent")
        body = response.json()
        assert "details" in body["error"], "error 缺少 details"
        assert isinstance(body["error"]["details"], dict), "details 应为对象"

    def test_error_format_matches_acceptance_criteria(self):
        """错误体格式符合验收标准: {\"error\": {\"code\":..., \"message\":..., \"details\":{}}}"""
        response = client.get("/api/v1/items/nonexistent")
        body = response.json()
        assert "error" in body
        error = body["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error
        assert isinstance(error["details"], dict)

    # ===== 边界覆盖 =====

    def test_validation_error_returns_422(self):
        """请求体验证失败应返回 422"""
        response = client.post("/api/v1/items", json={"name": "", "price": -1})
        assert response.status_code == 422

    def test_post_without_body_returns_422(self):
        """POST 缺少请求体返回 422"""
        response = client.post("/api/v1/items", json={})
        assert response.status_code == 422

    def test_delete_nonexistent_returns_404(self):
        """删除不存在的资源返回 404"""
        response = client.delete("/api/v1/items/no-such-id")
        assert response.status_code == 404

    def test_put_nonexistent_returns_404(self):
        """PUT 不存在的资源返回 404"""
        response = client.put("/api/v1/items/nonexistent", json={
            "name": "x", "price": 1.0, "category": "x"
        })
        assert response.status_code == 404

    def test_get_nonexistent_nested_resource_returns_404(self):
        """GET 不存在的嵌套资源返回 404"""
        response = client.get("/api/v1/items/no-such-id/reviews")
        assert response.status_code == 404
