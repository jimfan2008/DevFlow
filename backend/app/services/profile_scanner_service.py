from typing import List, Optional
from pydantic import BaseModel, Field
from app.utils.hermes_fs import (
    scan_all_profiles,
    read_profile_config,
    check_gateway_running,
)


class ProfileInfo(BaseModel):
    """Agent Profile 信息"""
    name: str
    model_default: Optional[str] = None
    model_provider: Optional[str] = None
    gateway_port: Optional[int] = None
    api_key: Optional[str] = None
    personality: Optional[str] = None
    is_running: bool = False
    config_path: str


class ProfileScannerService:
    """Profile 扫描服务 - 自动发现 Hermes Agent profiles"""

    def __init__(self):
        self._cache: List[ProfileInfo] = []
        self._cache_timestamp: float = 0

    async def get_all_profiles(self, force_refresh: bool = False) -> List[ProfileInfo]:
        """获取所有 profiles"""
        profiles_data = scan_all_profiles()
        return [ProfileInfo(**data) for data in profiles_data]

    async def get_profile(self, profile_name: str) -> Optional[ProfileInfo]:
        """获取单个 profile 信息"""
        profiles = await self.get_all_profiles()
        for profile in profiles:
            if profile.name == profile_name:
                return profile
        return None

    async def get_profile_status(self, profile_name: str) -> dict:
        """获取 profile 的运行状态"""
        config = read_profile_config(profile_name)
        is_running = check_gateway_running(profile_name)

        return {
            'name': profile_name,
            'is_running': is_running,
            'config_loaded': config is not None
        }


profile_scanner = ProfileScannerService()
