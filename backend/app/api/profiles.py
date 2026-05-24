from fastapi import APIRouter, HTTPException
from app.services.profile_scanner_service import profile_scanner
from app.schemas.hermes_skill import HermesSkillResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/profiles", tags=["profiles"], redirect_slashes=False)


class ProfileInfoResponse(BaseModel):
    name: str
    model_default: Optional[str] = None
    model_provider: Optional[str] = None
    gateway_port: Optional[int] = None
    personality: Optional[str] = None
    is_running: bool = False
    config_path: str


@router.get("", response_model=dict)
async def list_profiles():
    try:
        profiles = await profile_scanner.get_all_profiles()
        return {
            "code": 0,
            "message": "success",
            "data": {
                "profiles": [p.model_dump() for p in profiles],
                "total": len(profiles),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan profiles: {str(e)}")


@router.get("/{profile_name}", response_model=dict)
async def get_profile(profile_name: str):
    try:
        profile = await profile_scanner.get_profile(profile_name)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found")
        return {
            "code": 0,
            "message": "success",
            "data": profile.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@router.get("/{profile_name}/status", response_model=dict)
async def get_profile_status(profile_name: str):
    try:
        status = await profile_scanner.get_profile_status(profile_name)
        return {
            "code": 0,
            "message": "success",
            "data": status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")
