from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json

app = FastAPI(title="GBM HR OCR Service", version="1.0.0")

class OCRResult(BaseModel):
    field: str
    value: str
    confidence: float

class OCRResponse(BaseModel):
    success: bool
    data: List[OCRResult]
    message: Optional[str] = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ocr-service"}

@app.post("/api/v1/recognize", response_model=OCRResponse)
async def recognize(file: UploadFile = File(...)):
    """OCR 证件识别"""
    # TODO: 实现 PaddleOCR 识别逻辑
    return OCRResponse(
        success=True,
        data=[],
        message="OCR 识别完成"
    )
