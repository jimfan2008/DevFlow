from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

app = FastAPI(title="GBM HR RPA Service", version="1.0.0")

class RPATaskRequest(BaseModel):
    task_type: str
    target_url: str
    form_data: Optional[dict] = None
    employee_id: Optional[str] = None

class RPATaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rpa-service"}

@app.post("/api/v1/tasks", response_model=RPATaskResponse)
async def create_task(request: RPATaskRequest):
    """创建 RPA 任务"""
    # TODO: 实现 Playwright 浏览器自动化逻辑
    return RPATaskResponse(
        task_id="task_001",
        status="pending",
        message="RPA 任务已创建"
    )

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询 RPA 任务状态"""
    return {"task_id": task_id, "status": "pending"}
