

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Optional

from langchain_core.runnables import RunnableConfig

from app.infrastructure.load_llms import create_llm
from app.infrastructure.logger import Logging

from app.agents.Deduplication_Agent.graph.workflow import (
    build_deduplication_graph,
)
from app.agents.Deduplication_Agent.utils.helper import (
    build_initial_state,
    extract_deduplication_result,
)


class RequirementDeduplicationAgent:
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
        context_data = dict(context or {})

        company_id = (
            context_data.get("CompanyId")
            or context_data.get("companyId")
        )

        tender_id = (
            context_data.get("TenderId")
            or context_data.get("tenderId")
        )

        deduplication_id = (
            context_data.get("DeduplicationId")
            or correlation_id
        )

        requirement_count = (
            len(raw_requirements)
            if isinstance(
                raw_requirements,
                list,
            )
            else 0
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
            tracking_token["correlation_id"]
        )

        common_payload = {
            "companyId": company_id,
            "tenderId": tender_id,
            "deduplicationId": deduplication_id,
            "inputRequirementCount": (
                requirement_count
            ),
        }

        # start() only starts the timer, so explicitly
        # send the started event.
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
            initial_state = build_initial_state(
                raw_requirements=raw_requirements,
                context=context_data,
                bearer_token=bearer_token,
                correlation_id=(
                    effective_correlation_id
                ),
            )

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

            if not isinstance(summary, Mapping):
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
                "deduplicationStatus": "Completed",
            }

            await asyncio.to_thread(
                self._logger.end,
                tracking_token=tracking_token,
                is_success=True,
                message=(
                    "Requirement deduplication "
                    "completed"
                ),
                event_type=(
                    "RequirementDeduplicationCompleted"
                ),
                payload=completed_payload,
            )

            return result

        except Exception as exc:
            failed_payload = {
                **common_payload,
                "error": str(exc),
                "errorType": type(exc).__name__,
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