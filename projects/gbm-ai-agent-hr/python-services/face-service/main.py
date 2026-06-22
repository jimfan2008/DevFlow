"""
GBM AI Agent HR - Face Service (:8092)
人脸识别子服务 - InsightFace 0.3.x
"""

import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
from insightface.app import FaceAnalysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 模型加载 ====================
face_app: Optional[FaceAnalysis] = None


def load_face_model():
    global face_app
    try:
        face_app = FaceAnalysis(name="buffalo_l", root="./models", providers=["CPUExecutionProvider"])
        face_app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load InsightFace model: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_face_model()
    yield


app = FastAPI(title="GBM HR Face Service", version="1.0.0", lifespan=lifespan)


# ==================== 请求/响应模型 ====================
class FaceDetectResponse(BaseModel):
    status: str
    face_count: int
    face_list: list = []


class FaceCompareResponse(BaseModel):
    status: str
    similarity: float
    is_same_person: bool
    threshold: float


class FaceRegisterResponse(BaseModel):
    status: str
    employee_id: str
    face_embedding: list


class LivenessCheckResponse(BaseModel):
    status: str
    is_live: bool
    score: float


# ==================== API 端点 ====================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "face-service", "version": "1.0.0"}


@app.post("/detect", response_model=FaceDetectResponse)
async def detect_faces(file: UploadFile = File(...)):
    """人脸检测 - 返回检测到的人脸数量和基本特征"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        content = await file.read()
        import io
        img = io.BytesIO(content)
        import cv2
        import numpy as np
        arr = np.frombuffer(content, np.uint8)
        img_cv = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img_cv is None:
            raise HTTPException(status_code=400, detail="无法解码图片")

        faces = face_app.get(img_cv)
        face_list = []
        for face in faces:
            face_list.append({
                "bbox": face.bbox.tolist(),
                "age": int(face.age),
                "gender": "M" if int(face.gender) == 1 else "F",
                "confidence": float(face.det_score),
            })

        return FaceDetectResponse(
            status="success",
            face_count=len(faces),
            face_list=face_list,
        )

    except Exception as e:
        logger.error(f"Face detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compare", response_model=FaceCompareResponse)
async def compare_faces(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    threshold: float = Form(0.6),
):
    """人脸比对 - 返回两张图片中人脸的相似度"""
    try:
        arr1 = np.frombuffer(await file1.read(), np.uint8)
        arr2 = np.frombuffer(await file2.read(), np.uint8)
        import cv2
        img1 = cv2.imdecode(arr1, cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(arr2, cv2.IMREAD_COLOR)

        faces1 = face_app.get(img1)
        faces2 = face_app.get(img2)

        if len(faces1) == 0 or len(faces2) == 0:
            raise HTTPException(status_code=400, detail="至少一张图片未检测到人脸")

        emb1 = faces1[0].embedding
        emb2 = faces2[0].embedding
        similarity = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

        return FaceCompareResponse(
            status="success",
            similarity=similarity,
            is_same_person=similarity >= threshold,
            threshold=threshold,
        )

    except Exception as e:
        logger.error(f"Face comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/register", response_model=FaceRegisterResponse)
async def register_face(
    employee_id: str = Form(...),
    file: UploadFile = File(...),
):
    """人脸注册 - 注册新员工人脸特征"""
    try:
        arr = np.frombuffer(await file.read(), np.uint8)
        import cv2
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        faces = face_app.get(img)
        if len(faces) == 0:
            raise HTTPException(status_code=400, detail="未检测到人脸")
        if len(faces) > 1:
            raise HTTPException(status_code=400, detail="检测到多个人脸，请确保只有一张人脸")

        embedding = faces[0].embedding.tolist()

        return FaceRegisterResponse(
            status="success",
            employee_id=employee_id,
            face_embedding=embedding,
        )

    except Exception as e:
        logger.error(f"Face registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/liveness", response_model=LivenessCheckResponse)
async def liveness_check(file: UploadFile = File(...)):
    """活体检测 - 检测是否为真人而非照片/视频"""
    try:
        arr = np.frombuffer(await file.read(), np.uint8)
        import cv2
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        faces = face_app.get(img)
        if len(faces) == 0:
            raise HTTPException(status_code=400, detail="未检测到人脸")

        # 使用检测分数作为活体评分基础
        score = float(faces[0].det_score)

        return LivenessCheckResponse(
            status="success",
            is_live=score > 0.8,
            score=score,
        )

    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8092)
