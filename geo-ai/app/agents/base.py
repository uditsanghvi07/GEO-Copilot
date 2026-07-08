"""Abstract base class every agent must implement.

Design contract (mandatory, see project architecture rules):
- Each agent accepts a typed input schema and returns a typed output schema.
- Agents never call other agents directly; only the Orchestrator sequences
  multiple agents.
- Every agent is independently callable/testable via `execute()`, which
  wraps `run()` with start/end/duration logging and converts any exception
  into a typed, non-throwing `AgentResult(success=False, ...)` so a single
  agent failure never crashes the whole pipeline.
"""

import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from loguru import logger

from app.schemas.common import AgentResult

InputSchema = TypeVar("InputSchema")
OutputSchema = TypeVar("OutputSchema")


class BaseAgent(ABC, Generic[InputSchema, OutputSchema]):
    """Common interface implemented by every specialized agent."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short, unique, human-readable agent name (e.g. "website_crawler")."""
        raise NotImplementedError

    @abstractmethod
    async def run(self, input_data: InputSchema) -> OutputSchema:
        """Execute the agent's core logic.

        Inputs: input_data (agent-specific typed Pydantic schema).
        Outputs: agent-specific typed Pydantic schema.
        Implementations should raise on unrecoverable failure; `execute()`
        is responsible for catching and converting to `AgentResult`.
        """
        raise NotImplementedError

    async def execute(self, input_data: InputSchema) -> AgentResult:
        """Run the agent with standardized timing/logging and failure
        isolation.

        Inputs: input_data (agent-specific typed Pydantic schema).
        Outputs: `AgentResult` wrapping either the successful output data or
        an error message - never raises.
        """
        start = time.perf_counter()
        logger.info(f"[{self.name}] run started")
        try:
            output = await self.run(input_data)
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(f"[{self.name}] run succeeded in {duration_ms:.2f}ms")
            return AgentResult(success=True, data=output, error_message=None, duration_ms=duration_ms)
        except Exception as exc:  # noqa: BLE001 - agent failures must degrade gracefully
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(f"[{self.name}] run failed after {duration_ms:.2f}ms: {exc!r}")
            return AgentResult(
                success=False, data=None, error_message=str(exc), duration_ms=duration_ms
            )
