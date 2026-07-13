from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.Deduplication_Agent.graph.agent_state import (
    DeduplicationState,
)
from app.agents.Deduplication_Agent.graph.nodes import (
    deduplicate_requirements_node,
    prepare_prompt_node,
    validate_result_node,
)


def build_deduplication_graph(
    llm: Any,
):
    workflow = StateGraph(DeduplicationState)

    async def run_deduplication(
        state: DeduplicationState,
    ):
        return await deduplicate_requirements_node(
            state=state,
            llm=llm,
        )

    workflow.add_node(
        "prepare_prompt",
        prepare_prompt_node,
    )

    workflow.add_node(
        "deduplicate_requirements",
        run_deduplication,
    )

    workflow.add_node(
        "validate_result",
        validate_result_node,
    )

    workflow.add_edge(
        START,
        "prepare_prompt",
    )

    workflow.add_edge(
        "prepare_prompt",
        "deduplicate_requirements",
    )

    workflow.add_edge(
        "deduplicate_requirements",
        "validate_result",
    )

    workflow.add_edge(
        "validate_result",
        END,
    )

    return workflow.compile()