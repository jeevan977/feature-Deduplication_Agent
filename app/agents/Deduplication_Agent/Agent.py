

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Optional

from langchain_core.runnables import RunnableConfig

from app.infrastructure.load_llms import create_llm
from app.infrastructure.logger import Logging

from app.agents.Deduplication_Agent.graph.workflow import (
    build_deduplication_graph,
)
from app.utils.helpers import (
    build_initial_state,
    extract_deduplication_result,
    normalize_requirements,
)


class RequirementDeduplicationAgent:
    """
    Requirement Deduplication Agent.

    All normalized input requirements are sent through the
    LangGraph workflow in one invocation. The workflow therefore
    makes one LLM request and creates one token-usage log.
    """

    def __init__(
        self,
        llm: Any | None = None,
        graph: Any | None = None,
    ) -> None:
        self._llm = llm
        self._graph = graph

        self._logger = Logging(
            agent_name=(
                "Requirement Deduplication Agent"
            ),
            source_module=(
                "app.agents."
                "Deduplication_Agent.Agent"
            ),
        )

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = create_llm()

        return self._llm

    @property
    def graph(self) -> Any:
        if self._graph is None:
            self._graph = (
                build_deduplication_graph(
                    llm=self.llm,
                )
            )

        return self._graph

    async def deduplicate(
        self,
        raw_requirements: Any,
        *,
        context: Optional[
            Mapping[str, Any]
        ] = None,
        bearer_token: str | None = None,
        correlation_id: str | None = None,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        """
        Send the complete normalized requirement list to the LLM
        in one graph invocation.

        No candidate components, chunks or partitions are created.
        """

        context_data = dict(
            context or {}
        )

        requirements = normalize_requirements(
            raw_requirements
        )

        if not requirements:
            raise ValueError(
                "No requirements were supplied to Agent 1."
            )

        company_id = (
            context_data.get("CompanyId")
            or context_data.get("companyId")
            or context_data.get("company_id")
            or ""
        )

        tender_id = (
            context_data.get("TenderId")
            or context_data.get("tenderId")
            or context_data.get("tender_id")
            or ""
        )

        deduplication_id = (
            context_data.get("DeduplicationId")
            or context_data.get("deduplicationId")
            or correlation_id
            or ""
        )

        requirement_count = len(
            requirements
        )

        tracking_token = self._logger.start(
            message=(
                "Requirement deduplication "
                "processing started"
            ),
            event_type=(
                "RequirementDeduplicationStarted"
            ),
        )

        effective_correlation_id = (
            correlation_id
            or tracking_token[
                "correlation_id"
            ]
        )

        common_payload = {
            "companyId": str(
                company_id
            ),
            "tenderId": str(
                tender_id
            ),
            "deduplicationId": str(
                deduplication_id
            ),
            "inputRequirementCount": (
                requirement_count
            ),
            "llmInvocationMode": "OneGo",
            "llmInvocationCount": 1,
        }

        await asyncio.to_thread(
            self._logger.log,
            message=(
                "Requirement deduplication "
                "processing started"
            ),
            event_type=(
                "RequirementDeduplicationStarted"
            ),
            is_success=True,
            duration_ms=0,
            start_time=tracking_token[
                "start_time"
            ],
            end_time=None,
            payload=common_payload,
            correlation_id=(
                effective_correlation_id
            ),
        )

        try:
            print(
                "Sending all requirements to "
                "Agent 1 in one LLM invocation:",
                {
                    "requirementCount": (
                        requirement_count
                    ),
                    "partitioningEnabled": False,
                    "llmInvocationCount": 1,
                },
            )

            initial_state = build_initial_state(
                raw_requirements=requirements,
                context=context_data,
                bearer_token=bearer_token,
                correlation_id=(
                    effective_correlation_id
                ),
            )

            # Exactly one graph invocation.
            # The graph contains exactly one LLM node.
            final_state = await self.graph.ainvoke(
                initial_state,
                config=config,
            )

            result = (
                extract_deduplication_result(
                    final_state
                )
            )

            summary = result.get(
                "Summary",
                {},
            )

            if not isinstance(
                summary,
                Mapping,
            ):
                summary = {}

            completed_payload = {
                **common_payload,
                "totalInputRequirements": (
                    summary.get(
                        "TotalInputRequirements",
                        requirement_count,
                    )
                ),
                "totalDeduplicatedRequirements": (
                    summary.get(
                        "TotalDeduplicatedRequirements",
                        0,
                    )
                ),
                "duplicatesRemoved": (
                    summary.get(
                        "DuplicatesRemoved",
                        0,
                    )
                ),
                "deduplicationStatus": (
                    "Complete"
                ),
            }

            await asyncio.to_thread(
                self._logger.end,
                tracking_token=tracking_token,
                is_success=True,
                message=(
                    "Requirement deduplication "
                    "complete"
                ),
                event_type=(
                    "RequirementDeduplicationComplete"
                ),
                payload=completed_payload,
            )

            return result

        except Exception as exc:
            failed_payload = {
                **common_payload,
                "error": str(exc),
                "errorType": (
                    type(exc).__name__
                ),
            }

            await asyncio.to_thread(
                self._logger.end,
                tracking_token=tracking_token,
                is_success=False,
                message=(
                    "Requirement deduplication failed"
                ),
                event_type=(
                    "RequirementDeduplicationFailed"
                ),
                payload=failed_payload,
            )

            raise

    async def run(
        self,
        raw_requirements: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.deduplicate(
            raw_requirements=raw_requirements,
            **kwargs,
        )

    async def process(
        self,
        raw_requirements: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.deduplicate(
            raw_requirements=raw_requirements,
            **kwargs,
        )

    async def ainvoke(
        self,
        input_data: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.deduplicate(
            raw_requirements=input_data,
            config=config,
            **kwargs,
        )


DeduplicationAgent = (
    RequirementDeduplicationAgent
)

Agent = RequirementDeduplicationAgent