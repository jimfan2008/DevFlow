from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.hermes.types import (
    ChatChunk,
    HermesAPIError,
    SSEEvent,
)
from app.services.hermes.hermes_api_client import HermesAPIClient
from app.services.hermes.hermes_session import HermesSessionManager

logger = logging.getLogger("devflow.hermes.chat")

_concurrent_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore(max_concurrent: int = 5) -> asyncio.Semaphore:
    global _concurrent_semaphore
    if _concurrent_semaphore is None:
        _concurrent_semaphore = asyncio.Semaphore(max_concurrent)
    return _concurrent_semaphore


class ThinkingFilter:
    THINK_START = "<think>"
    THINK_END = "</think>"

    def __init__(self, show_thinking: bool = False):
        self._show = show_thinking
        self._in_thinking = False
        self._thinking_buf = ""
        self._content_buf = ""

    def filter_chunk(self, text: str) -> tuple[str, str]:
        thinking_out = ""
        content_out = ""
        i = 0
        while i < len(text):
            if not self._in_thinking:
                end_pos = text.find(self.THINK_START, i)
                if end_pos >= 0:
                    content_out += text[i:end_pos]
                    self._in_thinking = True
                    i = end_pos + len(self.THINK_START)
                else:
                    content_out += text[i:]
                    break
            else:
                end_pos = text.find(self.THINK_END, i)
                if end_pos >= 0:
                    self._thinking_buf += text[i:end_pos]
                    thinking_out += self._thinking_buf
                    self._thinking_buf = ""
                    self._in_thinking = False
                    i = end_pos + len(self.THINK_END)
                else:
                    self._thinking_buf += text[i:]
                    break
        if self._show:
            return thinking_out, content_out
        return "", content_out

    def flush(self) -> tuple[str, str]:
        thinking = ""
        content = ""
        if self._in_thinking and self._thinking_buf:
            if self._show:
                thinking = self._thinking_buf
            else:
                content = self._thinking_buf
        self._thinking_buf = ""
        self._in_thinking = False
        return thinking, content


def strip_thinking_process(text: str) -> str:
    patterns = [
        r'<think>.*?</think>',
        r'<tool_call>.*?👉',
        r'Thinking Process:.*?\n(?=[^\n]*[\u4e00-\u9fff{])',
    ]
    result = text
    for p in patterns:
        result = re.sub(p, '', result, flags=re.DOTALL | re.IGNORECASE)
    lines = result.strip().split('\n')
    clean = []
    in_english_block = False
    for line in lines:
        s = line.strip()
        if not s:
            clean.append(line)
            continue
        has_cjk = bool(re.search(r'[\u4e00-\u9fff]', s))
        if has_cjk:
            in_english_block = False
            clean.append(line)
        elif s.startswith(('#', '{', '[', '-', '*')) or re.match(r'^\d+\.\s', s):
            in_english_block = False
            clean.append(line)
        elif not in_english_block:
            in_english_block = True
            continue
        else:
            continue
    return '\n'.join(clean).strip() or text


class HermesChatService:
    def __init__(self, api_client: HermesAPIClient, db: Session, show_thinking: bool = False):
        self._api = api_client
        self._show_thinking = show_thinking

    async def stream_chat(
        self,
        session_id: str,
        message: str,
        model: str = None,
        profile_name: str = "default",
        history: List[Dict[str, str]] = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        sem = _get_semaphore()
        async with sem:
            messages = list(history or [])
            messages.append({"role": "user", "content": message})

            thinking_filter = ThinkingFilter(show_thinking=self._show_thinking)
            full_content = ""
            full_thinking = ""
            tool_calls_list = []

            yield SSEEvent(event="session", data={"session_id": session_id})

            try:
                async for chunk in self._api.chat_completions_stream(messages=messages, model=model):
                    if chunk.reasoning_content:
                        full_thinking += chunk.reasoning_content
                        if self._show_thinking:
                            yield SSEEvent(event="thinking", data={"content": chunk.reasoning_content})

                    if chunk.content:
                        t_out, c_out = thinking_filter.filter_chunk(chunk.content)
                        if t_out:
                            full_thinking += t_out
                            yield SSEEvent(event="thinking", data={"content": t_out})
                        if c_out:
                            full_content += c_out
                            yield SSEEvent(event="content", data={"content": c_out})

                    if chunk.tool_calls:
                        tool_calls_list.extend(chunk.tool_calls)
                        for tc in chunk.tool_calls:
                            yield SSEEvent(event="tool_call", data=tc)

                    if chunk.finish_reason:
                        t_flush, c_flush = thinking_filter.flush()
                        if c_flush:
                            full_content += c_flush
                            yield SSEEvent(event="content", data={"content": c_flush})

                cleaned_content = strip_thinking_process(full_content) if full_content else full_content
                if cleaned_content != full_content and full_content:
                    pass

                yield SSEEvent(event="done", data={
                    "content": cleaned_content or full_content,
                    "thinking_content": full_thinking if self._show_thinking else "",
                    "tool_calls": tool_calls_list,
                    "model": model or self._api._default_model,
                })

            except asyncio.CancelledError:
                yield SSEEvent(event="error", data={"type": "interrupted", "message": "对话已中断", "partial_content": full_content})

            except HermesAPIError as e:
                yield SSEEvent(event="error", data={"type": "api_error", "message": self._format_error(e)})

            except httpx.ConnectError:
                yield SSEEvent(event="error", data={"type": "disconnected", "message": "无法连接 Hermes Agent，请检查服务是否运行"})

            except Exception as e:
                logger.error(f"Stream chat error: {e}")
                yield SSEEvent(event="error", data={"type": "unknown", "message": f"对话出错：{str(e)[:200]}"})

    @staticmethod
    def _format_error(error: HermesAPIError) -> str:
        code = error.status_code
        if code == 401:
            return "API 密钥无效或已过期，请检查 HERMES_API_KEY 配置"
        if code == 429:
            return "请求过于频繁，请稍后重试"
        if code == 503:
            return "Hermes Agent 服务暂不可用，请稍后重试"
        if code >= 500:
            return f"Hermes Agent 服务错误（{code}），请检查服务状态"
        if code == 404:
            return "API 端点不存在，请检查 HERMES_API_BASE 配置"
        return f"请求失败（{code}）：{error.body[:100]}" if code else str(error)
