from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from app.graph.event_emitter import EventEmitter
from app.llm.adapter import llm_adapter
from app.llm.json_parser import NORMALIZERS, SCHEMA_EXAMPLES, parse_json_content
from common.logger import my_logger

logger = my_logger
PROMPTS_DIR = Path(__file__).parent / "prompts"

JSON_ONLY_SUFFIX = (
    "\n\n【重要】只输出一个 JSON 对象，不要 Markdown 代码块，不要任何解释文字。"
    "必须包含 overall 总分字段和 dimensions 各维度字段。"
)


class BaseAgent(ABC):
    agent_id: str = ""
    prompt_file: str = ""
    output_schema: Type[BaseModel]

    def load_system_prompt(self) -> str:
        path = PROMPTS_DIR / self.prompt_file
        return path.read_text(encoding="utf-8")

    @abstractmethod
    def build_user_prompt(self, input_data: BaseModel) -> str:
        ...

    def normalize_output(self, data: dict[str, Any]) -> dict[str, Any]:
        normalizer = NORMALIZERS.get(self.agent_id)
        if normalizer:
            return normalizer(data)
        return data

    def _validate(self, data: dict[str, Any]) -> BaseModel:
        normalized = self.normalize_output(data)
        return self.output_schema.model_validate(normalized)

    async def _parse_and_validate(
        self, system_prompt: str, user_prompt: str, raw_buffer: str
    ) -> BaseModel:
        schema_example = SCHEMA_EXAMPLES.get(self.agent_id, "")

        try:
            result_dict = parse_json_content(raw_buffer)
        except Exception:
            logger.warning("%s: 流式输出 JSON 解析失败，尝试非流式重试", self.agent_id)
            result_dict = await llm_adapter.chat_json(
                system_prompt + "\n\n你必须只输出合法 JSON。",
                user_prompt + JSON_ONLY_SUFFIX,
            )

        try:
            return self._validate(result_dict)
        except ValidationError as first_err:
            logger.warning("%s: Schema 校验失败，尝试修复: %s", self.agent_id, first_err)
            if not schema_example:
                raise

            repaired = await llm_adapter.repair_json(
                system_prompt,
                user_prompt,
                schema_example,
                raw_buffer or str(result_dict),
                str(first_err),
            )
            return self._validate(repaired)

    async def run(self, input_data: BaseModel, emitter: EventEmitter) -> BaseModel:
        system_prompt = self.load_system_prompt()
        user_prompt = self.build_user_prompt(input_data) + JSON_ONLY_SUFFIX

        chunk_index = 0
        buffer = ""

        async def _stream_logs() -> str:
            nonlocal chunk_index, buffer
            async for token in llm_adapter.stream(system_prompt, user_prompt):
                buffer += token
                if token.strip():
                    await emitter.emit_agent_log(
                        agent=self.agent_id,
                        content=token,
                        chunk_index=chunk_index,
                    )
                    chunk_index += 1
            return buffer

        try:
            buffer = await asyncio.wait_for(_stream_logs(), timeout=120)
        except asyncio.TimeoutError as exc:
            from app.utils.exceptions import AgentTimeoutError

            raise AgentTimeoutError(f"{self.agent_id} 执行超时") from exc

        validated = await self._parse_and_validate(system_prompt, user_prompt, buffer)
        await emitter.emit_stage_result(agent=self.agent_id, result=validated.model_dump())
        return validated
