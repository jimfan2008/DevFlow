import json
import re
import httpx
import asyncio
import subprocess
import shutil
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.utils.hermes_fs import (
    read_profile_config,
    get_gateway_port_from_config,
    get_gateway_api_key,
    check_gateway_running,
    get_hermes_home_path,
)
import logging

logger = logging.getLogger("devflow.gateway_client")

MAX_CONCURRENT = 20
REQUEST_TIMEOUT = 360
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)

HERMES_CLI_PATH = shutil.which("hermes")


class GatewayClient:
    def __init__(self, profile_name: str = None, port: int = None, timeout: int = REQUEST_TIMEOUT):
        self.profile_name = profile_name or "default"
        self.port = port
        self.timeout = timeout
        self._api_key: Optional[str] = None
        self._use_cli = False

    def _get_base_url(self) -> str:
        if self.port:
            import os
            host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
            return f"http://{host}:{self.port}"
        return ""

    def _get_headers(self, api_key: str = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key = api_key or self._api_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def _resolve_profile(self) -> tuple:
        if self.port:
            return self.port, self._api_key
        config = read_profile_config(self.profile_name)
        if config:
            port = get_gateway_port_from_config(config)
            api_key = get_gateway_api_key(config) or ""

            if port:
                # 检查 api_server 是否已连接
                import json, os
                gw_state_path = os.path.join(
                    get_hermes_home_path(), "profiles", self.profile_name, "gateway_state.json"
                )
                api_server_connected = False
                try:
                    with open(gw_state_path) as f:
                        state = json.load(f)
                    api_server_connected = (state.get("platforms", {})
                                            .get("api_server", {})
                                            .get("state") == "connected")
                except Exception:
                    pass

                if api_server_connected:
                    self.port = port
                    self._api_key = api_key
                    return port, api_key

                # api_server 未标记 connected，尝试直接连接端口
                import httpx as _httpx
                try:
                    test_url = f"http://localhost:{port}/v1/chat/completions"
                    with _httpx.Client(timeout=5) as _client:
                        _resp = _client.post(
                            test_url,
                            json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
                            headers={"Content-Type": "application/json"}
                            | ({"Authorization": f"Bearer {api_key}"} if api_key else {}),
                        )
                        if _resp.status_code in (200, 201, 401, 422):
                            self.port = port
                            self._api_key = api_key
                            logger.info(f"Port {port} reachable for profile '{self.profile_name}', using gateway HTTP")
                            return port, api_key
                except Exception:
                    pass
                logger.warning(f"Port {port} unreachable for profile '{self.profile_name}', will try other methods")

        # Fallback: extract port from HERMES_API_BASE env var
        import os
        api_base = os.environ.get("HERMES_API_BASE", "")
        if api_base:
            from urllib.parse import urlparse
            parsed = urlparse(api_base)
            if parsed.port:
                api_key = os.environ.get("HERMES_API_KEY", "")
                test_url = f"http://{parsed.hostname}:{parsed.port}/v1/chat/completions"
                try:
                    import httpx as _httpx
                    with _httpx.Client(timeout=5) as _client:
                        _resp = _client.post(test_url, json={"model": "test", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1}, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"} if api_key else {"Content-Type": "application/json"})
                        if _resp.status_code not in (200, 201, 401, 422):
                            logger.warning(f"HERMES_API_BASE port {parsed.port} returned {_resp.status_code} for /v1/chat/completions, falling back to CLI")
                            self._use_cli = True
                            return 0, ""
                except Exception as e:
                    logger.warning(f"HERMES_API_BASE port {parsed.port} unreachable: {e}, falling back to CLI")
                    self._use_cli = True
                    return 0, ""
                self.port = parsed.port
                self._api_key = api_key or None
                logger.info(f"Using HERMES_API_BASE port {parsed.port} for profile '{self.profile_name}'")
                return parsed.port, api_key

        if check_gateway_running(self.profile_name):
            self._use_cli = True
            logger.info(f"用hermes CLI调用Agent profile '{self.profile_name}'")
            return 0, ""

        raise ValueError(f"Gateway not available for profile '{self.profile_name}'. Ensure Hermes Gateway is running with API server enabled or install hermes CLI.")

    async def _cli_send(self, message: str) -> str:
        global HERMES_CLI_PATH
        if not HERMES_CLI_PATH:
            hermes_home = get_hermes_home_path()
            cli_candidates = [
                str(hermes_home / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"),
                str(hermes_home / "hermes-agent" / "venv" / "bin" / "hermes"),
                "hermes",
            ]
            for candidate in cli_candidates:
                if shutil.which(candidate):
                    HERMES_CLI_PATH = candidate
                    break

        if not HERMES_CLI_PATH:
            raise ConnectionError("Hermes CLI not found. Install hermes or enable Gateway API server.")

        msg_preview = message[:80].replace('\n', '\\n')
        logger.info(f"[GATEWAY_DEBUG] CLI调用: {HERMES_CLI_PATH} chat -q \"{msg_preview}...\" --profile {self.profile_name}")

        def _run_cli():
            return subprocess.run(
                [HERMES_CLI_PATH, "chat", "-q", message, "--profile", self.profile_name],
                capture_output=True, text=True, timeout=self.timeout,
            )

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_run_cli),
                timeout=self.timeout
            )
            if result.returncode == 0:
                stdout = result.stdout.strip()
                logger.info(f"[GATEWAY_DEBUG] CLI返回: returncode=0, stdout_len={len(stdout)}, preview={stdout[:200]}")
                if result.stderr:
                    logger.info(f"[GATEWAY_DEBUG] CLI stderr: {result.stderr[:200]}")
                return stdout
            else:
                logger.error(f"[GATEWAY_DEBUG] CLI错误: returncode={result.returncode}, stderr={result.stderr[:500]}")
                raise Exception(f"hermes CLI error: {result.stderr}")
        except asyncio.TimeoutError:
            logger.error(f"[GATEWAY_DEBUG] CLI超时 (timeout={self.timeout}s)")
            raise TimeoutError(f"hermes CLI timed out after {self.timeout}s")

    async def _cli_send_stream(self, message: str):
        """CLI流式输出：用Popen逐行读取，实时yield"""
        global HERMES_CLI_PATH
        if not HERMES_CLI_PATH:
            hermes_home = get_hermes_home_path()
            cli_candidates = [
                str(hermes_home / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"),
                str(hermes_home / "hermes-agent" / "venv" / "bin" / "hermes"),
                "hermes",
            ]
            for candidate in cli_candidates:
                if shutil.which(candidate):
                    HERMES_CLI_PATH = candidate
                    break
        if not HERMES_CLI_PATH:
            raise ConnectionError("Hermes CLI not found")

        msg_preview = message[:80].replace('\n', '\\n')
        logger.info(f"[GATEWAY_DEBUG] CLI流式调用: profile={self.profile_name}, msg={msg_preview}...")

        proc = await asyncio.create_subprocess_exec(
            HERMES_CLI_PATH, "chat", "-q", message, "--profile", self.profile_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info(f"[GATEWAY_DEBUG] CLI进程已启动 pid={proc.pid}")
        full_text = ""
        async for line in proc.stdout:
            text = line.decode("utf-8", errors="replace")
            full_text += text
            yield text
        await proc.wait()
        logger.info(f"[GATEWAY_DEBUG] CLI进程结束 returncode={proc.returncode}, total_len={len(full_text)}")

    async def chat_completions(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        model: str = "hermes-agent",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        port, api_key = await self._resolve_profile()
        
        if self._use_cli:
            logger.info(f"[GATEWAY_DEBUG] chat_completions CLI模式: profile={self.profile_name}, messages={len(messages)}条, stream={stream}")
            combined = "\n".join(m.get("content", "") for m in messages if m.get("content"))
            if stream:
                async for chunk in self._cli_send_stream(combined):
                    yield chunk
            else:
                result = await self._cli_send(combined)
                yield result
            return
            
        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with _semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if stream:
                        async with client.stream("POST", url, headers=headers, json=payload) as response:
                            if response.status_code != 200:
                                error_text = await response.aread()
                                raise Exception(f"Gateway error {response.status_code}: {error_text.decode()}")
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    if data == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data)
                                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if content:
                                            yield content
                                    except json.JSONDecodeError:
                                        continue
                    else:
                        response = await client.post(url, headers=headers, json=payload)
                        if response.status_code != 200:
                            raise Exception(f"Gateway error {response.status_code}: {response.text}")
                        result = response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        yield content
            except httpx.TimeoutException:
                raise TimeoutError(f"Request timed out after {self.timeout}s")
            except httpx.ConnectError:
                raise ConnectionError(f"Cannot connect to gateway at port {port}")
            except Exception as e:
                raise

    async def send_message(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        messages = conversation_history or []
        messages.append({"role": "user", "content": message})
        async for chunk in self.chat_completions(messages=messages, stream=stream):
            yield chunk

    async def send_message_non_stream(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> str:
        full_response = []
        async for chunk in self.send_message(message, conversation_history, stream=False):
            full_response.append(chunk)
        return "".join(full_response)

    async def stream_message(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self.send_message(message, conversation_history, stream=True):
            yield chunk

    async def health_check(self) -> bool:
        if self._use_cli:
            return check_gateway_running(self.profile_name)
        try:
            port, api_key = await self._resolve_profile()
        except Exception:
            return check_gateway_running(self.profile_name)
        if self._use_cli:
            return check_gateway_running(self.profile_name)
        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                return resp.status_code == 200
        except Exception:
            return check_gateway_running(self.profile_name)

    async def chat_isolated(
        self,
        messages: List[Dict[str, str]],
        project_id: str,
        project_name: str,
        project_description: str = "",
        core_goal: str = "",
        agent_name: str = "",
        stream: bool = False,
        max_tokens: int = 2000,
    ) -> AsyncGenerator[str, None]:
        """项目隔离的对话模式
        
        核心问题：Hermes gateway 在每次请求时加载 profile 的 memory.md/user.md，
        导致 A 项目的上下文会泄漏到 B 项目。
        
        解决方案：
        1. 构建强力的项目隔离系统消息，明确指定当前项目
        2. 指示 LLM 忽略记忆中其他项目的信息
        3. 使用 HTTP API 模式（无状态请求）
        """
        # 构建项目隔离的系统消息
        system_content_parts = []
        
        if agent_name:
            system_content_parts.append(
                f"你是{agent_name}，DevFlow 16步开发流程中的专业角色。"
            )
        
        system_content_parts.append(
            f"\n【当前项目上下文】\n"
            f"项目名称: {project_name}\n"
            f"项目ID: {project_id}"
        )
        
        if project_description:
            system_content_parts.append(f"项目描述: {project_description}")
        
        if core_goal:
            system_content_parts.append(f"核心目标: {core_goal}")
        
        system_content_parts.append(
            "\n【重要工作规则 - 项目隔离】\n"
            "1. 你正在为上述「当前项目」工作\n"
            "2. 请只引用上述项目信息，不要引用其他任何项目的上下文\n"
            "3. 如果你的记忆中存在其他项目的信息，请完全忽略它们\n"
            "4. 所有回答、分析、设计都只针对当前项目\n"
            "5. 不得将其他项目的数据、需求、设计带入当前项目"
        )
        
        system_message = {"role": "system", "content": "\n".join(system_content_parts)}
        
        # 将系统消息作为第一条消息
        isolated_messages = [system_message]
        
        # 过滤并添加用户提供的消息
        for msg in messages:
            # 跳过用户可能传入的旧系统消息，使用我们构建的新系统消息
            if msg.get("role") == "system":
                continue
            isolated_messages.append(msg)
        
        # 使用 HTTP API 模式发送（无状态，不加载 profile 的会话历史）
        port, api_key = await self._resolve_profile()
        logger.info(f"[GATEWAY_DEBUG] profile={self.profile_name} 解析完成: _use_cli={self._use_cli}, port={port}, has_api_key={bool(api_key)}")
        
        if self._use_cli:
            logger.info(f"[GATEWAY_DEBUG] chat_isolated CLI模式: profile={self.profile_name}, stream={stream}")
            combined = "\n".join(m.get("content", "") for m in isolated_messages if m.get("content"))
            if stream:
                async for chunk in self._cli_send_stream(combined):
                    yield chunk
            else:
                result = await self._cli_send(combined)
                yield result
            return
        
        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)

        # Try to get model from profile config, fallback to gpt-4o
        model = "gpt-4o"
        try:
            config = read_profile_config(self.profile_name)
            if config:
                default_model = config.get("model", {})
                if isinstance(default_model, dict):
                    model = default_model.get("default", "gpt-4o")
                elif isinstance(default_model, str):
                    model = default_model
        except Exception:
            pass

        payload = {
            "model": model,
            "messages": isolated_messages,
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        logger.info(f"[GATEWAY_DEBUG] HTTP调用 houfu: url={url}, model={model}, stream={stream}, max_tokens={max_tokens}")
        
        async with _semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if stream:
                        async with client.stream("POST", url, headers=headers, json=payload) as response:
                            logger.info(f"[GATEWAY_DEBUG] houfu HTTP响应状态码: {response.status_code}")
                            if response.status_code != 200:
                                error_text = await response.aread()
                                logger.error(f"[GATEWAY_DEBUG] houfu HTTP错误: {response.status_code} {error_text.decode()[:200]}")
                                raise Exception(f"Gateway error {response.status_code}: {error_text.decode()}")
                            logger.info(f"[GATEWAY_DEBUG] ✅ houfu HTTP连接成功，开始接收流式响应...")
                            chunk_idx = 0
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    data = line[6:]
                                    if data == "[DONE]":
                                        logger.info(f"[GATEWAY_DEBUG] houfu 流式响应结束 [DONE]")
                                        break
                                    try:
                                        chunk = json.loads(data)
                                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if content:
                                            chunk_idx += 1
                                            if chunk_idx == 1:
                                                logger.info(f"[GATEWAY_DEBUG] ✅ houfu 第一个chunk到达! content={content[:60]}")
                                            yield content
                                    except json.JSONDecodeError:
                                        continue
                            logger.info(f"[GATEWAY_DEBUG] houfu 流式响应结束，共{chunk_idx}个chunk")
                    else:
                        response = await client.post(url, headers=headers, json=payload)
                        logger.info(f"[GATEWAY_DEBUG] houfu HTTP响应状态码: {response.status_code}")
                        if response.status_code != 200:
                            logger.error(f"[GATEWAY_DEBUG] houfu HTTP错误: {response.status_code} {response.text[:200]}")
                            raise Exception(f"Gateway error {response.status_code}: {response.text}")
                        result = response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        logger.info(f"[GATEWAY_DEBUG] ✅ houfu 非流式响应完成: {len(content)}字符")
                        yield content
            except httpx.TimeoutException:
                logger.error(f"[GATEWAY_DEBUG] ❌ houfu 请求超时 (timeout={self.timeout}s)")
                raise TimeoutError(f"Request timed out after {self.timeout}s")
            except httpx.ConnectError:
                logger.error(f"[GATEWAY_DEBUG] ❌ 无法连接到houfu gateway: host={host}, port={port}")
                raise ConnectionError(f"Cannot connect to gateway at port {port}")

    # ── 自动授权 ──

    AUTHORIZATION_PATTERNS = re.compile(
        r'需要您的批准|请老板批准|需要您的授权|请批准|需要授权|'
        r'需要.*批准.*执行|请.*同意.*执行|需要.*确认.*执行|'
        r'please.*approve|need.*approval|require.*authorization|'
        r'consent.*required|execute_code.*批准|批准.*execute_code',
        re.IGNORECASE,
    )

    AUTHORIZATION_RESPONSE = "同意，授权执行。请继续完成上述任务，无需再请求批准。"

    def _needs_authorization(self, text: str) -> bool:
        return bool(self.AUTHORIZATION_PATTERNS.search(text))

    async def _send_approval(
        self,
        messages: List[Dict[str, str]],
        approval_text: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Send approval as follow-up and yield the agent's continuation."""
        approved_messages = messages + [
            {"role": "assistant", "content": messages[-1].get("content", "")},
            {"role": "user", "content": approval_text},
        ]
        port, api_key = await self._resolve_profile()

        if self._use_cli:
            combined = "\n".join(m.get("content", "") for m in approved_messages if m.get("content"))
            async for chunk in self._cli_send_stream(combined):
                yield chunk
            return

        import os
        host = os.environ.get("HERMES_GATEWAY_HOST", "localhost")
        url = f"http://{host}:{port}/v1/chat/completions"
        headers = self._get_headers(api_key)
        payload = {
            "model": model,
            "messages": approved_messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with _semaphore:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"[AUTO_AUTH] Gateway error {response.status_code}: {error_text.decode()[:200]}")
                        return
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

    async def chat_completions_with_auto_auth(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        model: str = "hermes-agent",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_auth_rounds: int = 3,
    ) -> AsyncGenerator[str, None]:
        """chat_completions with automatic authorization.

        If the agent's response contains an authorization request pattern,
        automatically sends an approval follow-up and yields the continuation.
        """
        all_chunks: List[str] = []

        async for chunk in self.chat_completions(
            messages=messages, stream=stream, model=model,
            temperature=temperature, max_tokens=max_tokens,
        ):
            all_chunks.append(chunk)
            yield chunk

        full_response = "".join(all_chunks)

        for _ in range(max_auth_rounds):
            if not self._needs_authorization(full_response):
                break

            logger.info(f"[AUTO_AUTH] Agent requested authorization, auto-approving (profile={self.profile_name})")
            approval_chunks: List[str] = []

            async for chunk in self._send_approval(
                messages=messages, approval_text=self.AUTHORIZATION_RESPONSE,
                model=model, temperature=temperature, max_tokens=max_tokens,
            ):
                approval_chunks.append(chunk)
                yield chunk

            full_response = "".join(approval_chunks)

    async def chat_isolated_with_auto_auth(
        self,
        messages: List[Dict[str, str]],
        project_id: str,
        project_name: str,
        project_description: str = "",
        core_goal: str = "",
        agent_name: str = "",
        stream: bool = False,
        max_tokens: int = 2000,
        max_auth_rounds: int = 3,
    ) -> AsyncGenerator[str, None]:
        """chat_isolated with automatic authorization."""
        # Build the full isolated messages (same as chat_isolated does internally)
        system_content_parts = []
        if agent_name:
            system_content_parts.append(f"你是{agent_name}，DevFlow 16步开发流程中的专业角色。")
        system_content_parts.append(
            f"\n【当前项目上下文】\n项目名称: {project_name}\n项目ID: {project_id}"
        )
        if project_description:
            system_content_parts.append(f"项目描述: {project_description}")
        if core_goal:
            system_content_parts.append(f"核心目标: {core_goal}")
        system_content_parts.append(
            "\n【重要工作规则 - 项目隔离】\n"
            "1. 你正在为上述「当前项目」工作\n"
            "2. 请只引用上述项目信息，不要引用其他任何项目的上下文\n"
            "3. 如果你的记忆中存在其他项目的信息，请完全忽略它们\n"
            "4. 所有回答、分析、设计都只针对当前项目\n"
            "5. 不得将其他项目的数据、需求、设计带入当前项目"
        )
        full_messages = [{"role": "system", "content": "\n".join(system_content_parts)}]
        for msg in messages:
            if msg.get("role") == "system":
                continue
            full_messages.append(msg)

        all_chunks: List[str] = []

        async for chunk in self.chat_isolated(
            messages=messages, project_id=project_id, project_name=project_name,
            project_description=project_description, core_goal=core_goal,
            agent_name=agent_name, stream=stream, max_tokens=max_tokens,
        ):
            all_chunks.append(chunk)
            yield chunk

        full_response = "".join(all_chunks)

        for _ in range(max_auth_rounds):
            if not self._needs_authorization(full_response):
                break

            logger.info(f"[AUTO_AUTH] Agent requested authorization, auto-approving (profile={self.profile_name})")
            approval_chunks: List[str] = []

            async for chunk in self._send_approval(
                messages=full_messages, approval_text=self.AUTHORIZATION_RESPONSE,
                model="gpt-4o", temperature=0.7, max_tokens=max_tokens,
            ):
                approval_chunks.append(chunk)
                yield chunk

            full_response = "".join(approval_chunks)


gateway_client = GatewayClient()
