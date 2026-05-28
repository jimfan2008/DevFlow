"""Hermes 自动发现与自动配置服务

功能：
1. 扫描本地机器上的 Hermes 安装（多种路径）
2. 如果 Hermes 未配置 Gateway Port -> 自动配置
3. 注册到 DevFlow Agent 管理（新建或更新）
4. 验证连通性
"""
from __future__ import annotations

import os
import sys
import yaml
import json
import logging
import subprocess
import platform
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger("devflow.hermes_discovery")

# ================================================================
# 已知钩子事件类型 (供参考)
# ================================================================
KNOWN_HOOK_EVENTS = [
    "gateway:startup",    # 网关启动
    "session:start",      # 新会话开始
    "session:end",        # 会话结束
    "session:reset",      # 会话重置
    "agent:start",        # 智能体开始处理
    "agent:step",         # 智能体每一步
    "agent:end",          # 智能体结束处理
    "command:*",          # 任意斜杠命令触发
]


# ================================================================
# 部分1: 自动发现 Hermes 安装
# ================================================================

def _windows_locations() -> List[str]:
    """返回 Windows 上常见的 Hermes 安装路径。"""
    homes = []
    lo = os.environ.get("LOCALAPPDATA", "")
    ro = os.environ.get("APPDATA", "")
    hm = str(Path.home())

    # 常见的安装变体
    candidates = [
        os.path.join(lo, "hermes"),                              # C:\Users\...\AppData\Local\hermes
        os.path.join(ro, "hermes"),                              # C:\Users\...\AppData\Roaming\hermes
        os.path.join(lo, "hermes", "hermes-agent"),              # C:\Users\...\AppData\Local\hermes\hermes-agent
        os.path.join(hm, ".hermes"),                              # C:\Users\Lenovo\.hermes
    ]
    for c in candidates:
        if os.path.isdir(c):
            homes.append(c)

    return list(dict.fromkeys(homes))  # 去重且保持顺序


def _generic_locations() -> List[str]:
    """非 Windows 系统上的常见路径。"""
    locs = []
    hm = str(Path.home())
    for p in [
        os.path.join(hm, ".hermes"),
        os.path.join(hm, ".hermes", "hermes-agent"),
        os.path.expanduser("~/hermes"),
    ]:
        if os.path.isdir(p):
            locs.append(p)
    return locs


def scan_for_hermes_installations() -> List[str]:
    """
    扫描本机发现所有赫尔墨斯安装。

    返回发现的安装根目录列表。
    """
    if platform.system() == "Windows":
        locs = _windows_locations()
    else:
        locs = _generic_locations()
    return locs


def is_valid_hermes_install(root: str) -> bool:
    """判断目录是否为有效的赫尔墨斯安装。"""
    p = Path(root)
    return (p / "config.yaml").is_file() or (p / "hermes-agent").is_dir()


# ================================================================
# 第二部分: 读取配置
# ================================================================

def read_hermes_config(root: str) -> Optional[Dict[str, Any]]:
    """
    从安装根目录读取 config.yaml。
    支持多种可能的 config.yaml 位置。
    """
    for rel in ["config.yaml", "hermes-agent/config.yaml"]:
        path = Path(root) / rel
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if isinstance(cfg, dict):
                    return cfg
            except Exception as e:
                logger.warning(f"读取配置失败 {path}: {e}")
    return None


def read_hermes_env(root: str) -> Dict[str, str]:
    """从 .env 文件读取密钥和环境变量。"""
    result: Dict[str, str] = {}
    env_path = Path(root) / ".env"
    if not env_path.is_file():
        return result
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line or raw_line.startswith("#"):
                    continue
                if "=" not in raw_line:
                    continue
                key, _, value = raw_line.partition("=")
                result[key.strip()] = value.strip()
    except Exception as e:
        logger.warning(f"读取 .env 失败 {root}: {e}")
    return result


def read_hermes_soul(root: str) -> Optional[str]:
    """读取人格描述 (SOUL.md)。"""
    for rel in ["SOUL.md", "hermes-agent/SOUL.md"]:
        p = Path(root) / rel
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8")[:300]
            except Exception:
                pass
    return None


def detect_hermes_version(root: str) -> str:
    """检测 Hermes 的版本。"""
    for cmd in ["hermes --version", "hermes-agent --version"]:
        try:
            out = subprocess.check_output(
                cmd, shell=True, timeout=5, stderr=subprocess.DEVNULL
            ).decode().strip()
            if out:
                return out.split("\n")[0][:100]
        except Exception:
            pass
    # 尝试从 pyproject.toml
    for rel in ["pyproject.toml", "hermes-agent/pyproject.toml"]:
        pt = Path(root) / rel
        if pt.is_file():
            try:
                with open(pt, encoding="utf-8") as f:
                    content = f.read()
                for line in content.split("\n"):
                    if line.startswith('version ='):
                        v = line.split('"')[1] if '"' in line else line.split("'")[1]
                        return v[:30]
            except Exception:
                pass
    return "unknown"


def extract_profile_info(root: str) -> Dict[str, Any]:
    """从赫尔墨斯安装中提取关键配置信息。"""
    config = read_hermes_config(root) or {}
    env_data = read_hermes_env(root)
    soul = read_hermes_soul(root)
    version = detect_hermes_version(root)

    # 提取模型信息
    model_cfg = config.get("model", {}) or {}
    model_provider = model_cfg.get("provider", "").upper()
    if model_provider and model_provider.endswith("_OPENROUTER_OPENAI_COMPATIBLE"):
        model_provider = "OPENROUTER"
    elif model_provider and model_provider.endswith("_COMPATIBLE"):
        model_provider = model_provider.rsplit("_", 1)[0]
    elif model_provider:
        model_provider = model_provider.upper()[:20]

    model_name = (
        model_cfg.get("default", "")
        or model_cfg.get("primary_model", "")
        or ""
    )
    model_name = model_name or env_data.get("MODEL_NAME", "") or ""

    # 从配置中获取 Gateway 端口
    gw_port = None
    platforms = config.get("platforms", {}) or {}
    api_server = platforms.get("api_server", {}) or {}
    extra = api_server.get("extra", {}) or {}

    try:
        raw_port = extra.get("port")
        if raw_port is not None:
            gw_port = int(raw_port)
    except (ValueError, TypeError):
        pass

    # API key
    api_key_env = env_data.get("HERMES_API_KEY") or env_data.get("OPENROUTER_API_KEY", "")
    has_api_key = bool(api_key_env)

    # Hooks
    hooks_cfg = config.get("hooks", {}) or {}
    hooks_auto_accept = config.get("hooks_auto_accept", False)

    return {
        "location": root,
        "has_gateway_port": gw_port is not None,
        "gateway_port": gw_port,
        "model_provider": model_provider,
        "model_name": model_name,
        "has_api_key": has_api_key,
        "hooks_enabled": bool(hooks_cfg),
        "hooks_auto_accept": bool(hooks_auto_accept),
        "known_hook_events": KNOWN_HOOK_EVENTS,
        "personality_snippet": soul[:80] if soul else None,
        "version": version,
        "config_raw": config,
        "env_partial": {k: v[:20] + "***" for k, v in env_data.items()},
    }


# ================================================================
# 第三部分: 自动配置 Gateway Port
# ================================================================

DEFAULT_GW_PORT = 8081


def _pick_free_port(start: int = DEFAULT_GW_PORT, max_attempts: int = 100) -> Optional[int]:
    """选择一个可用的本地端口。"""
    import socket
    for offset in range(max_attempts):
        port = start + offset
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", port))
            sock.close()
            return port
        except OSError:
            sock.close()
            continue
    return None


def auto_configure_gateway_port(
    installation_root: str,
    port_override: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    为赫尔墨斯配置 Gateway HTTP 端口。

    如果赫尔墨斯的 config.yaml 中已配置 `platforms.api_server.extra.port`，则跳过。
    否则，写入一个新的端口号并修改文件。
    """
    result = {
        "installation": installation_root,
        "original_port": None,
        "new_port": None,
        "modified": False,
        "dry_run": dry_run,
        "error": None,
    }

    config_path = Path(installation_root) / "config.yaml"
    if not config_path.is_file():
        result["error"] = "未找到 config.yaml"
        return result

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        result["error"] = f"读取配置失败: {e}"
        return result

    platforms = config.setdefault("platforms", {})
    api_server = platforms.setdefault("api_server", {})
    extra = api_server.setdefault("extra", {})

    result["original_port"] = extra.get("port")

    if extra.get("port"):
        result["error"] = "已配置 Gateway 端口，跳过"
        return result

    port_to_use = port_override if port_override else _pick_free_port()
    if not port_to_use:
        result["error"] = "无法找到空闲端口"
        return result

    if dry_run:
        result["dry_port_proposal"] = port_to_use
        result["dry_change_note"] = (
            f"Hermes 需要配置端口 {port_to_use} 以便 DevFlow 通过 "
            f"http://localhost:{port_to_use}/v1/chat/completions 通讯。"
        )
        return result

    try:
        extra["port"] = port_to_use
        # 如果缺少 api_server，添加基本配置
        if "key" not in api_server:
            api_server["key"] = "devflow-auto-generated"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        result["new_port"] = port_to_use
        result["modified"] = True
    except Exception as e:
        result["error"] = f"写入配置失败: {e}"

    return result


# ================================================================
# 第四部分: 注册到 DevFlow Agent 管理
# ================================================================

def _register_hermes_agent(
    db: Session,
    profile_info: Dict[str, Any],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    将从赫尔墨斯发现的信息注册到 DevFlow 的 Agent 表中。
    如果已存在则更新。
    """
    from app.models.agent import Agent

    location = profile_info["location"]
    name = profile_info.get("gateway_port") or str(hash(location) & 0xFFFFFFFF)
    # 使用 location 的最后一部分作为友好名
    friendly_name = Path(location).parts[-1] if Path(location).parts else location

    existing = (
        db.query(Agent)
        .filter(Agent.name == friendly_name, Agent.agent_type == "hermes")
        .first()
    )

    if existing:
        logger.info(f"[discovery] Existing agent found: {friendly_name}, updating.")
        profile_info_copy = {**profile_info}
        profile_info_copy.pop("config_raw", None)
        profile_info_copy.pop("env_partial", None)
        existing.config = profile_info_copy
        existing.status = "offline"  # 需要心跳才能上线
        db.commit()
        db.refresh(existing)
        return {"action": "updated", "agent_id": existing.id, "agent_name": existing.name}

    # 创建新 Agent 记录
    _gw_host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
    agent = Agent(
        name=friendly_name,
        agent_type="hermes",
        status="offline",
        api_endpoint=(
            f"http://{_gw_host}:{profile_info.get('gateway_port')}"
            if profile_info.get("gateway_port") else None
        ),
        config={k: v for k, v in profile_info.items() if k not in ("config_raw", "env_partial")},
        discovered_by="profile_scan",
        profile_path=location,
        created_by=user_id,
    )
    db.add(agent)
    try:
        db.commit()
        db.refresh(agent)
        return {"action": "created", "agent_id": agent.id, "agent_name": agent.name}
    except Exception as e:
        db.rollback()
        logger.error(f"[discovery] 注册 Agent 失败: {e}")
        return {"action": "error", "error": str(e)}


# ================================================================
# 第五部分: 统一的自动化流程
# ================================================================

def autodetect_and_register(
    db: Session,
    user_id: Optional[str] = None,
    auto_configure: bool = False,
    force_scan: bool = False,
) -> Dict[str, Any]:
    """
    完整的自动发现 + 注册流水线。

    返回值:
    {
        "instances_found": [...],  # 已存在的实例详情
        "actions_taken": [...],    # 执行的操作
        "warnings": [...]         # 警告信息
    }
    """
    actions: List[Dict[str, Any]] = []
    found: List[Dict[str, Any]] = []
    warnings: List[str] = []

    # 1. 扫描所有可能的赫尔墨斯安装
    roots = scan_for_hermes_installations()
    logger.info(f"[autodetect] Scanned {len(roots)} potential locations.")

    # 2. 对每个安装提取信息
    profiles: List[Dict[str, Any]] = []
    for root in roots:
        if not is_valid_hermes_install(root):
            continue
        profile = extract_profile_info(root)
        profiles.append(profile)
        found.append(profile)

    # 3. 如果没有已配置的 Gateway 端口，自动配置
    if auto_configure:
        for profile in profiles:
            if not profile["has_gateway_port"]:
                cfg_result = auto_configure_gateway_port(
                    profile["location"],
                    dry_run=False,
                )
                if cfg_result.get("modified"):
                    profile["gateway_port"] = cfg_result["new_port"]
                    profile["has_gateway_port"] = True
                    actions.append({
                        "action": "configured_gateway_port",
                        "installation": profile["location"],
                        "port": cfg_result["new_port"],
                    })
                    warnings.append(
                        f"已为 {profile['location']} 配置 Gateway 端口 "
                        f"{cfg_result['new_port']}。需要重启赫尔墨斯才生效。"
                    )
                else:
                    warnings.append(
                        f"自动配置 Gateway 端口失败 "
                        f"{profile['location']}: {cfg_result.get('error', '未知错误')}"
                    )

    # 4. 注册到 Agent 表
    for profile in profiles:
        reg = _register_hermes_agent(db, profile, user_id)
        actions.append(reg)

    return {
        "instances_found": len(found),
        "actions": actions,
        "warnings": warnings,
        "profiles": found,
    }


def autodetect_and_register_simple(
    db: Session,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    简化的自动发现 — 仅扫描 + 注册（不修改配置文件）。

    推荐在生产中使用此方法以避免意外修改用户的赫尔墨斯配置。
    """
    return autodetect_and_register(
        db=db, user_id=user_id, auto_configure=False
    )
