import json
import re
from typing import Any, AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.json_parser import parse_json_content
from app.utils.exceptions import LLMError
from common.llm import my_llm
from common.logger import my_logger

logger = my_logger


class LLMAdapter:
    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        try:
            async for chunk in my_llm.astream(messages):
                if chunk.content:
                    yield str(chunk.content)
        except Exception as exc:
            logger.error("LLM stream failed: %s", exc)
            raise LLMError(str(exc)) from exc

    async def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        try:
            response = await my_llm.ainvoke(messages)
            content = str(response.content)
            return parse_json_content(content)
        except LLMError:
            raise
        except Exception as exc:
            logger.error("LLM invoke failed: %s", exc)
            raise LLMError(str(exc)) from exc

    async def repair_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_example: str,
        raw_output: str,
        validation_error: str,
    ) -> dict[str, Any]:
        repair_prompt = (
            f"{user_prompt}\n\n"
            f"你上一次的输出无法通过 Schema 校验。\n"
            f"校验错误：{validation_error}\n"
            f"上一次输出片段：{raw_output[:2000]}\n\n"
            f"请严格只输出 JSON，必须符合以下结构（字段名不可更改）：\n"
            f"{schema_example}"
        )
        return await self.chat_json(
            system_prompt + "\n\n你必须只输出合法 JSON，禁止 Markdown 和解释文字。",
            repair_prompt,
        )


llm_adapter = LLMAdapter()

# 向后兼容
__all__ = ["LLMAdapter", "llm_adapter", "parse_json_content"]
