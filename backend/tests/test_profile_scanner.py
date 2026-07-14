"""v4.0 Profile Scanner Tests - Hermes Agent自动发现（SRS 3.7.2）"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.profile_scanner_service import ProfileScannerService, ProfileInfo


class TestProfileInfoModel:
    """ProfileInfo 数据模型测试"""

    def test_profile_info_required_fields(self):
        info = ProfileInfo(name="haimei", config_path="/home/user/.hermes/profiles/haimei")
        assert info.name == "haimei"
        assert info.config_path == "/home/user/.hermes/profiles/haimei"
        assert info.is_running is False
        assert info.model_default is None

    def test_profile_info_full_fields(self):
        info = ProfileInfo(
            name="houxing", model_default="gpt-4o", model_provider="openai",
            gateway_port=8766, personality="需求分析师",
            is_running=True, config_path="/home/user/.hermes/profiles/houxing/config.yaml",
        )
        assert info.name == "houxing"
        assert info.gateway_port == 8766
        assert info.is_running is True
        assert info.model_provider == "openai"

    def test_profile_info_default_is_running(self):
        info = ProfileInfo(name="test", config_path="/path")
        assert info.is_running is False

    def test_profile_info_optional_api_key(self):
        info = ProfileInfo(name="test", config_path="/path", api_key="sk-xxx")
        assert info.api_key == "sk-xxx"

    def test_profile_info_str_representation(self):
        info = ProfileInfo(name="haimei", config_path="/path")
        assert "haimei" in str(info)


class TestProfileScannerService:
    """Profile 扫描服务测试"""

    @pytest.mark.asyncio
    async def test_get_all_profiles(self):
        with patch('app.services.profile_scanner_service.scan_all_profiles',
                   return_value=[
                       {"name": "haimei", "config_path": "/profiles/haimei"},
                       {"name": "houxing", "config_path": "/profiles/houxing"},
                   ]):
            svc = ProfileScannerService()
            profiles = await svc.get_all_profiles()
            assert len(profiles) == 2
            assert profiles[0].name == "haimei"
            assert profiles[1].name == "houxing"

    @pytest.mark.asyncio
    async def test_get_all_profiles_empty(self):
        with patch('app.services.profile_scanner_service.scan_all_profiles',
                   return_value=[]):
            svc = ProfileScannerService()
            profiles = await svc.get_all_profiles()
            assert profiles == []

    @pytest.mark.asyncio
    async def test_get_profile_found(self):
        with patch('app.services.profile_scanner_service.scan_all_profiles',
                   return_value=[
                       {"name": "haimei", "config_path": "/profiles/haimei"},
                       {"name": "houxing", "config_path": "/profiles/houxing"},
                   ]):
            svc = ProfileScannerService()
            profile = await svc.get_profile("haimei")
            assert profile is not None
            assert profile.name == "haimei"

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self):
        with patch('app.services.profile_scanner_service.scan_all_profiles',
                   return_value=[
                       {"name": "haimei", "config_path": "/profiles/haimei"},
                   ]):
            svc = ProfileScannerService()
            profile = await svc.get_profile("nonexistent")
            assert profile is None

    @pytest.mark.asyncio
    async def test_get_profile_status_running(self):
        with patch('app.services.profile_scanner_service.read_profile_config',
                   return_value={"name": "haimei", "gateway_port": 8765}):
            with patch('app.services.profile_scanner_service.check_gateway_running',
                       return_value=True):
                svc = ProfileScannerService()
                status = await svc.get_profile_status("haimei")
                assert status["name"] == "haimei"
                assert status["is_running"] is True
                assert status["config_loaded"] is True

    @pytest.mark.asyncio
    async def test_get_profile_status_offline(self):
        with patch('app.services.profile_scanner_service.read_profile_config',
                   return_value={"name": "test", "gateway_port": 7777}):
            with patch('app.services.profile_scanner_service.check_gateway_running',
                       return_value=False):
                svc = ProfileScannerService()
                status = await svc.get_profile_status("test")
                assert status["is_running"] is False

    @pytest.mark.asyncio
    async def test_get_profile_status_no_config(self):
        with patch('app.services.profile_scanner_service.read_profile_config',
                   return_value=None):
            with patch('app.services.profile_scanner_service.check_gateway_running',
                       return_value=False):
                svc = ProfileScannerService()
                status = await svc.get_profile_status("unknown")
                assert status["config_loaded"] is False


class TestProfileScannerCache:
    """Profile 缓存机制测试"""

    @pytest.mark.asyncio
    async def test_cache_initialized_empty(self):
        svc = ProfileScannerService()
        assert svc._cache == []
        assert svc._cache_timestamp == 0

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self):
        with patch('app.services.profile_scanner_service.scan_all_profiles') as mock_scan:
            mock_scan.return_value = [{"name": "haimei", "config_path": "/path"}]
            svc = ProfileScannerService()
            profiles1 = await svc.get_all_profiles(force_refresh=True)
            assert len(profiles1) == 1
            profiles2 = await svc.get_all_profiles(force_refresh=True)
            assert len(profiles2) == 1
            assert mock_scan.call_count == 2


class TestProfileScannerEdgeCases:
    """Profile 扫描边界情况测试"""

    @pytest.mark.asyncio
    async def test_scan_all_profiles_error_handling(self):
        with patch('app.services.profile_scanner_service.scan_all_profiles',
                   side_effect=Exception("扫描异常")):
            svc = ProfileScannerService()
            with pytest.raises(Exception, match="扫描异常"):
                await svc.get_all_profiles()

    @pytest.mark.asyncio
    async def test_get_profile_with_special_chars(self):
        with patch('app.services.profile_scanner_service.scan_all_profiles',
                   return_value=[
                       {"name": "haimei-2", "config_path": "/path"},
                       {"name": "hou_xing", "config_path": "/path"},
                   ]):
            svc = ProfileScannerService()
            p1 = await svc.get_profile("haimei-2")
            assert p1 is not None
            p2 = await svc.get_profile("hou_xing")
            assert p2 is not None

    @pytest.mark.asyncio
    async def test_ten_named_agents_discoverable(self):
        expected_names = {
            "haimei", "houxing", "houwang", "houfa", "houda",
            "houfu", "hougui", "hourong", "houhua",
        }
        with patch('app.services.profile_scanner_service.scan_all_profiles',
                   return_value=[{"name": n, "config_path": f"/path/{n}"}
                                 for n in expected_names]):
            svc = ProfileScannerService()
            profiles = await svc.get_all_profiles()
            actual_names = {p.name for p in profiles}
            assert actual_names == expected_names
            assert len(profiles) == 9
