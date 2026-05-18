import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional

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
    logger.warning("acp package not installed; ACP functionality disabled")

logger = logging.getLogger("devflow.hermes.acp")

HERMES_BIN = "/home/jim/.hermes/hermes-agent/venv/bin/hermes"


class HermesACPClient(Client):
    """ACP client for DevFlow -> Hermes Agent communication over stdio.

    Implements the acp.Client protocol and manages the lifecycle of
    the underlying 'hermes acp' subprocess.
    """

    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.connection: Optional[ClientSideConnection] = None
        self._session_id: Optional[str] = None
        self._accumulated_response: list[str] = []

    async def start(self):
        """Spawn hermes acp and connect via stdio."""
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
        """Initialize ACP session."""
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
        """Send a prompt to Hermes and get the final response text."""
        sid = session_id or self._session_id
        if not sid:
            raise RuntimeError("No active ACP session")

        self._accumulated_response = []

        # Use the non-deprecated API: prompt=..., session_id=... (not PromptRequest wrapper)
        resp: PromptResponse = await self.connection.prompt(
            prompt=[TextContentBlock(type="text", text=message)],
            session_id=sid,
        )

        result = self._extract_prompt_result(resp)
        return result

    def _extract_prompt_result(self, resp: PromptResponse) -> str:
        """Extract text from PromptResponse and accumulated chunks."""
        accumulated = "".join(self._accumulated_response)
        self._accumulated_response = []
        return accumulated

    async def close(self):
        """Close the ACP connection and process."""
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

    # ── Client protocol implementation ──────────────────────────

    def on_connect(self, conn):
        logger.info("ACP on_connect called")

    async def session_update(
        self,
        session_id: str,
        update: UserMessageChunk | AgentMessageChunk | AgentThoughtChunk
        | ToolCallStart | ToolCallProgress | AgentPlanUpdate
        | AvailableCommandsUpdate | CurrentModeUpdate
        | ConfigOptionUpdate | SessionInfoUpdate | UsageUpdate,
    ) -> None:
        """Handle streaming updates from Hermes."""
        logger.debug("ACP session update for %s: %s", session_id, type(update).__name__)

        if isinstance(update, AgentMessageChunk):
            content = update.content
            if isinstance(content, TextContentBlock):
                self._accumulated_response.append(content.text)

    async def request_permission(
        self,
        options,
        session_id: str,
        tool_call,
    ) -> RequestPermissionResponse:
        """Auto-approve all permission requests for non-interactive use."""
        from acp.schema import RequestPermissionResponse, AllowedOutcome
        return RequestPermissionResponse(
            outcome=AllowedOutcome(type="allowed"),
        )

    async def write_text_file(
        self,
        content: str,
        path: str,
        session_id: str,
    ) -> WriteTextFileResponse | None:
        logger.debug("ACP write_text_file (stub): %s", path)
        return None

    async def read_text_file(
        self,
        path: str,
        session_id: str,
        limit: int | None = None,
        line: int | None = None,
    ) -> ReadTextFileResponse:
        from acp.schema import ReadTextFileResponse
        raise NotImplementedError("read_text_file not implemented on DevFlow client side")

    async def create_terminal(
        self,
        command: str,
        session_id: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: list | None = None,
        output_byte_limit: int | None = None,
    ) -> CreateTerminalResponse:
        from acp.schema import CreateTerminalResponse
        raise NotImplementedError("create_terminal not implemented on DevFlow client side")

    async def terminal_output(
        self,
        session_id: str,
        terminal_id: str,
    ) -> TerminalOutputResponse:
        from acp.schema import TerminalOutputResponse
        raise NotImplementedError("terminal_output not implemented on DevFlow client side")

    async def release_terminal(
        self,
        session_id: str,
        terminal_id: str,
    ) -> ReleaseTerminalResponse | None:
        return None

    async def wait_for_terminal_exit(
        self,
        session_id: str,
        terminal_id: str,
    ) -> WaitForTerminalExitResponse:
        from acp.schema import WaitForTerminalExitResponse
        raise NotImplementedError("wait_for_terminal_exit not implemented on DevFlow client side")

    async def kill_terminal(
        self,
        session_id: str,
        terminal_id: str,
    ) -> KillTerminalResponse | None:
        return None

    async def ext_method(self, method: str, params: dict):
        logger.debug("ACP ext_method (stub): %s", method)
        return None

    async def ext_notification(self, method: str, params: dict):
        logger.debug("ACP ext_notification (stub): %s", method)


_acp_client_instance: Optional[HermesACPClient] = None


def get_acp_client() -> HermesACPClient:
    global _acp_client_instance
    if _acp_client_instance is None:
        _acp_client_instance = HermesACPClient()
    return _acp_client_instance
