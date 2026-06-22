from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
import json

app = FastAPI(title="GBM HR Face Service", version="1.0.0")

class FaceCompareRequest(BaseModel):
    image1_b64: str
    image2_b64: str
    threshold: float = 0.38

class FaceCompareResponse(BaseModel):
    is_same_person: bool
    similarity: float
    threshold: float

class FaceDetectResponse(BaseModel):
    success: bool
    face_count: int
    embeddings: list

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "face-service"}

@app.post("/api/v1/compare", response_model=FaceCompareResponse)
async def compare_faces(request: FaceCompareRequest):
    """人脸比对"""
    # TODO: 实现 InsightFace 人脸比对逻辑
    return FaceCompareResponse(
        is_same_person=True,
        similarity=0.95,
        threshold=request.threshold
    )

@app.post("/api/v1/detect")
async def detect_face(file: UploadFile = File(...)):
    """人脸检测与特征提取"""
    # TODO: 实现人脸检测和特征提取
    return {"success": True, "face_count": 1}
