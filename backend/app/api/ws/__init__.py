from fastapi import APIRouter

from app.api.ws.router import router as main_router
from app.api.ws.step3_chat import router as step3_chat_router
from app.api.ws.step3_qa import router as step3_qa_router
from app.api.ws.step4_progress import router as step4_progress_router
from app.api.ws.step5_progress import router as step5_progress_router
from app.api.ws.step6_progress import router as step6_progress_router
from app.api.ws.step7_progress import router as step7_progress_router
from app.api.ws.step8_progress import router as step8_progress_router

router = APIRouter()
router.include_router(main_router)
router.include_router(step3_chat_router)
router.include_router(step3_qa_router)
router.include_router(step4_progress_router)
router.include_router(step5_progress_router)
router.include_router(step6_progress_router)
router.include_router(step7_progress_router)
router.include_router(step8_progress_router)
