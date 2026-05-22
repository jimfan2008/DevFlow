import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Any

try:
    from acp import Client, connect_to_agent, PROTOCOL_VERSION
    from acp.core import ClientSideConnection
    from acp.schema import (
        TextContentBlock,
        NewSessionRequest,
        NewSessionResponse,
        PromptRequest,
        PromptResponse,
        InitializeRequest,
        InitializeResponse,
        ClientCapabilities,
        Implementation,
        SessionNotification,
        AgentMessageChunk,
        AgentThoughtChunk,
        ToolCallStart,
        ToolCallProgress,
        AgentPlanUpdate,
        AvailableCommandsUpdate,
        CurrentModeUpdate,
        ConfigOptionUpdate,
        SessionInfoUpdate,
        UsageUpdate,
        UserMessageChunk,
        RequestPermissionRequest,
        RequestPermissionResponse,
        WriteTextFileRequest,
        WriteTextFileResponse,
        ReadTextFileRequest,
        ReadTextFileResponse,
        CreateTerminalRequest,
        CreateTerminalResponse,
        TerminalOutputRequest,
        TerminalOutputResponse,
        ReleaseTerminalRequest,
        ReleaseTerminalResponse,
        WaitForTerminalExitRequest,
        WaitForTerminalExitResponse,
        KillTerminalRequest,
        KillTerminalResponse,
        StopReason,
        TextContent,
    )
    ACP_AVAILABLE = True
except ImportError:
    Client = object  # type: ignore
    ACP_AVAILABLE = False

logger = logging.getLogger("devflow.hermes.acp")
logger.addHandler(logging.NullHandler())

HERMES_BIN = "/home/jim/.hermes/hermes-agent/venv/bin/hermes"

_acp_client_instance: Optional[Any] = None


def get_acp_client() -> Any:
    global _acp_client_instance
    if _acp_client_instance is None:
        _acp_client_instance = HermesACPClient()  # type: ignore[assignment]
    return _acp_client_instance


if not ACP_AVAILABLE:
    class HermesACPClient:
        """Stub when acp package is not installed."""

        process: Any = None
        connection: Any = None
        _session_id: Optional[str] = None
        _accumulated_response: list = []

        async def start(self) -> None:
            pass

        async def init_session(self, cwd: str = "/") -> str:
            self._session_id = "stub-session"
            return "stub-session"

        async def send_prompt(self, message: str, session_id: Optional[str] = None) -> str:
            return "stub-response"

        async def close(self) -> None:
            pass

else:
    class HermesACPClient(Client):  # type: ignore
        """ACP client for DevFlow -> Hermes Agent communication over stdio."""

        def __init__(self):
            self.process: Optional[asyncio.subprocess.Process] = None
            self.connection: Optional[ClientSideConnection] = None
            self._session_id: Optional[str] = None
            self._accumulated_response: list[str] = []

        async def start(self) -> None:
            logger.info("Starting Hermes ACP client, spawning: %s acp", HERMES_BIN)
            self.process = await asyncio.create_subprocess_exec(
                HERMES_BIN, "acp",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if not self.process.stdin or not self.process.stdout:
                raise RuntimeError("Failed to spawn hermes acp subprocess")
            self.connection = connect_to_agent(
                client=self,
                input_stream=self.process.stdin,
                output_stream=self.process.stdout,
            )
            logger.info("ACP client connected to hermes acp")

        async def init_session(self, cwd: str = "/") -> str:
            await self.connection.initialize(
                protocol_version=PROTOCOL_VERSION,
                client_capabilities=ClientCapabilities(),
                client_info=Implementation(name="DevFlow", version="1.0.0"),
            )
            resp: NewSessionResponse = await self.connection.new_session(cwd=cwd)
            self._session_id = resp.session_id
            logger.info("ACP session created: %s", self._session_id)
            return self._session_id

        async def send_prompt(self, message: str, session_id: Optional[str] = None) -> str:
            sid = session_id or self._session_id
            if not sid:
                raise RuntimeError("No active ACP session")
            self._accumulated_response = []
            resp: PromptResponse = await self.connection.prompt(
                prompt=[TextContentBlock(type="text", text=message)],
                session_id=sid,
            )
            return self._extract_prompt_result(resp)

        def _extract_prompt_result(self, resp: PromptResponse) -> str:
            accumulated = "".join(self._accumulated_response)
            self._accumulated_response = []
            return accumulated

        async def close(self) -> None:
            try:
                if self.connection and self._session_id:
                    await self.connection.close_session(session_id=self._session_id)
            except Exception:
                pass
            try:
                if self.process:
                    self.process.terminate()
                    await asyncio.sleep(0.5)
                    if self.process.returncode is None:
                        self.process.kill()
            except Exception:
                pass

        def on_connect(self, conn) -> None:
            logger.info("ACP on_connect called")

        async def session_update(
            self,
            session_id: str,
            update: Any,
        ) -> None:
            logger.debug("ACP session update for %s: %s", session_id, type(update).__name__)
            if isinstance(update, AgentMessageChunk):
                content = update.content
                if isinstance(content, TextContentBlock):
                    self._accumulated_response.append(content.text)

        async def request_permission(
            self,
            options: Any,
            session_id: str,
            tool_call: Any,
        ) -> RequestPermissionResponse:
            from acp.schema import AllowedOutcome
            return RequestPermissionResponse(outcome=AllowedOutcome(type="allowed"))

        async def write_text_file(
            self, content: str, path: str, session_id: str
        ) -> WriteTextFileResponse | None:
            logger.debug("ACP write_text_file (stub): %s", path)
            return None

        async def read_text_file(self, path: str, session_id: str,
                                 limit: int | None = None,
                                 line: int | None = None) -> ReadTextFileResponse:
            raise NotImplementedError("read_text_file not implemented on DevFlow client side")

        async def create_terminal(
            self, command: str, session_id: str,
            args: list[str] | None = None,
            cwd: str | None = None,
            env: list | None = None,
            output_byte_limit: int | None = None,
        ) -> CreateTerminalResponse:
            raise NotImplementedError("create_terminal not implemented")

        async def terminal_output(self, session_id: str, terminal_id: str) -> TerminalOutputResponse:
            raise NotImplementedError("terminal_output not implemented")

        async def release_terminal(self, session_id: str, terminal_id: str) -> Any | None:
            return None

        async def wait_for_terminal_exit(self, session_id: str, terminal_id: str) -> Any:
            raise NotImplementedError("wait_for_terminal_exit not implemented")

        async def kill_terminal(self, session_id: str, terminal_id: str) -> Any | None:
            return None

        async def ext_method(self, method: str, params: dict) -> Any:
            logger.debug("ACP ext_method (stub): %s", method)
            return None

        async def ext_notification(self, method: str, params: dict) -> None:
            logger.debug("ACP ext_notification (stub): %s", method)
