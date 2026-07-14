

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Sequence

from app.agents.Deduplication_Agent.graph.agent_state import (
    DeduplicationState,
)


def convert_to_plain_value(value: Any) -> Any:
    """
    Convert Pydantic models, dataclasses and other values
    into normal Python dictionaries and lists.
    """

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")

    if is_dataclass(value):
        return asdict(value)

    if isinstance(value, Mapping):
        return {
            str(key): convert_to_plain_value(item)
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [
            convert_to_plain_value(item)
            for item in value
        ]

    return value


def normalize_requirements(
    raw_requirements: Any,
) -> list[Any]:
    """
    Convert requirement input into a normal list.
    """

    raw_requirements = convert_to_plain_value(
        raw_requirements
    )

    if raw_requirements is None:
        return []

    if isinstance(raw_requirements, str):
        requirement_text = raw_requirements.strip()

        if not requirement_text:
            return []

        return [requirement_text]

    if isinstance(raw_requirements, Mapping):
        possible_keys = (
            "RawRequirements",
            "raw_requirements",
            "Requirements",
            "requirements",
            "Items",
            "items",
        )

        for key in possible_keys:
            value = raw_requirements.get(key)

            if value is not None:
                return normalize_requirements(value)

        return [dict(raw_requirements)]

    if isinstance(raw_requirements, Sequence) and not isinstance(
        raw_requirements,
        (str, bytes, bytearray),
    ):
        return [
            item
            for item in list(raw_requirements)
            if item is not None and item != ""
        ]

    return [raw_requirements]


def get_requirement_text(
    requirement: Any,
) -> str:
    """
    Extract readable requirement text from different
    possible requirement object structures.
    """

    if isinstance(requirement, str):
        return requirement.strip()

    if isinstance(requirement, Mapping):
        possible_text_keys = (
            "RequirementText",
            "requirement_text",
            "Text",
            "text",
            "Requirement",
            "requirement",
            "Description",
            "description",
            "Content",
            "content",
        )

        for key in possible_text_keys:
            value = requirement.get(key)

            if value is not None:
                text = str(value).strip()

                if text:
                    return text

    return json.dumps(
        requirement,
        ensure_ascii=False,
        default=str,
        sort_keys=True,
    )


def get_requirement_id(
    requirement: Any,
    index: int,
) -> str:
    """
    Extract requirement ID. Create a temporary ID
    when the input does not contain one.
    """

    if isinstance(requirement, Mapping):
        possible_id_keys = (
            "RequirementId",
            "requirement_id",
            "Id",
            "id",
            "_id",
        )

        for key in possible_id_keys:
            value = requirement.get(key)

            if value is not None:
                requirement_id = str(value).strip()

                if requirement_id:
                    return requirement_id

    return f"REQ-{index:04d}"


def build_initial_state(
    raw_requirements: Any,
    context: Mapping[str, Any] | None = None,
    bearer_token: str | None = None,
    correlation_id: str | None = None,
) -> DeduplicationState:
    """
    Create the initial LangGraph state.
    """

    requirements = normalize_requirements(
        raw_requirements
    )

    if not requirements:
        raise ValueError(
            "raw_requirements cannot be empty"
        )

    return DeduplicationState(
        raw_requirements=requirements,
        context=dict(context or {}),
        bearer_token=bearer_token,
        correlation_id=correlation_id,
        prompt="",
        llm_response=None,
        result={},
        error=None,
    )


def build_deduplication_prompt(
    raw_requirements: Any,
    context: Mapping[str, Any] | None = None,
) -> str:
    """
    Build the requirement deduplication prompt.

    This is the function that was missing and causing
    your ImportError.
    """

    requirements = normalize_requirements(
        raw_requirements
    )

    if not requirements:
        raise ValueError(
            "Cannot build prompt because no requirements were supplied"
        )

    indexed_requirements = []

    for index, requirement in enumerate(
        requirements,
        start=1,
    ):
        indexed_requirements.append(
            {
                "RequirementIndex": index,
                "RequirementId": get_requirement_id(
                    requirement,
                    index,
                ),
                "RequirementText": get_requirement_text(
                    requirement
                ),
                "OriginalRequirement": requirement,
            }
        )

    context_payload = dict(context or {})

    return f"""
You are a Requirement Deduplication Agent for tender and procurement requirements.

Your task is to identify requirements that express the same material obligation.

Do not classify requirements as duplicates only because they contain similar
keywords or belong to the same topic.

Requirements are duplicates only when satisfying one requirement would
substantially satisfy the other requirement.

Rules:

1. Preserve important scope, quantities, dates, locations, standards,
   evidence requirements, service levels, exclusions and compliance conditions.

2. Requirements with materially different conditions must remain separate.

3. Every input requirement must appear exactly once.

4. Every requirement must appear either inside one duplicate group or inside
   UniqueRequirementIndexes.

5. RequirementIndexes are 1-based indexes from the supplied requirement list.

6. A duplicate group must contain at least two different RequirementIndexes.

7. Return valid JSON only.

8. Do not return markdown code blocks.

Context:

{json.dumps(
    context_payload,
    ensure_ascii=False,
    default=str,
    indent=2,
)}

Requirements:

{json.dumps(
    indexed_requirements,
    ensure_ascii=False,
    default=str,
    indent=2,
)}

Return exactly this JSON structure:

{{
  "DuplicateGroups": [
    {{
      "CanonicalRequirement": "Complete consolidated requirement",
      "RequirementIndexes": [1, 2],
      "Reason": "Explanation of why the requirements are duplicates"
    }}
  ],
  "UniqueRequirementIndexes": [3, 4]
}}
""".strip()


def extract_response_content(
    llm_response: Any,
) -> Any:
    """
    Extract response content from LangChain messages
    and normal response objects.
    """

    if llm_response is None:
        raise ValueError(
            "LLM returned no response"
        )

    if isinstance(
        llm_response,
        (dict, list),
    ):
        return llm_response

    content = getattr(
        llm_response,
        "content",
        None,
    )

    if content is not None:
        if isinstance(content, list):
            text_parts: list[str] = []

            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)

                elif isinstance(part, Mapping):
                    text = (
                        part.get("text")
                        or part.get("content")
                    )

                    if text is not None:
                        text_parts.append(str(text))

            return "\n".join(text_parts)

        return content

    return str(llm_response)


def remove_markdown_code_fence(
    text: str,
) -> str:
    """
    Remove ```json code fences from an LLM response.
    """

    text = text.strip()

    fenced_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if fenced_match:
        return fenced_match.group(1).strip()

    return text


def decode_json_response(
    text: str,
) -> Any:
    """
    Decode JSON even when the model accidentally adds
    some text before or after the JSON object.
    """

    text = remove_markdown_code_fence(text)

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()

    for position, character in enumerate(text):
        if character not in "[{":
            continue

        try:
            parsed_value, _ = decoder.raw_decode(
                text[position:]
            )

            return parsed_value

        except json.JSONDecodeError:
            continue

    raise ValueError(
        "LLM response did not contain valid JSON. "
        f"Response preview: {text[:500]}"
    )


def parse_llm_response(
    llm_response: Any,
) -> dict[str, Any]:
    """
    Convert the LLM response into a Python dictionary.
    """

    content = extract_response_content(
        llm_response
    )

    if isinstance(content, Mapping):
        parsed_result = dict(content)

    elif isinstance(content, list):
        parsed_result = {
            "DuplicateGroups": content
        }

    else:
        decoded_value = decode_json_response(
            str(content)
        )

        if not isinstance(
            decoded_value,
            Mapping,
        ):
            raise ValueError(
                "LLM JSON response must be an object"
            )

        parsed_result = dict(decoded_value)

    possible_wrapper_keys = (
        "result",
        "Result",
        "output",
        "Output",
        "data",
        "Data",
    )

    for wrapper_key in possible_wrapper_keys:
        wrapped_result = parsed_result.get(
            wrapper_key
        )

        if isinstance(
            wrapped_result,
            Mapping,
        ):
            parsed_result = dict(
                wrapped_result
            )
            break

    return parsed_result


def get_first_value(
    mapping: Mapping[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    """
    Get the first available value using multiple
    possible property names.
    """

    for key in keys:
        if key in mapping:
            return mapping[key]

    return default


def normalize_indexes(
    value: Any,
    total_requirements: int,
) -> list[int]:
    """
    Convert LLM indexes into a valid unique list.
    """

    if value is None:
        return []

    if not isinstance(
        value,
        Sequence,
    ) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        value = [value]

    indexes: list[int] = []

    for item in value:
        try:
            index = int(item)

        except (TypeError, ValueError):
            continue

        if (
            1 <= index <= total_requirements
            and index not in indexes
        ):
            indexes.append(index)

    return indexes


def validate_deduplication_result(
    result: Any,
    raw_requirements: Any,
) -> dict[str, Any]:
    """
    Validate and normalize the LLM deduplication result.

    Requirements missing from the LLM output are automatically
    treated as unique so no requirement is accidentally lost.
    """

    requirements = normalize_requirements(
        raw_requirements
    )

    if not requirements:
        raise ValueError(
            "No raw requirements are available for validation"
        )

    if not isinstance(result, Mapping):
        raise ValueError(
            "Deduplication result must be a dictionary"
        )

    total_requirements = len(requirements)

    raw_duplicate_groups = get_first_value(
        result,
        "DuplicateGroups",
        "duplicate_groups",
        "Groups",
        "groups",
        default=[],
    )

    if not isinstance(
        raw_duplicate_groups,
        Sequence,
    ) or isinstance(
        raw_duplicate_groups,
        (str, bytes, bytearray),
    ):
        raw_duplicate_groups = []

    assigned_indexes: set[int] = set()
    validated_groups: list[dict[str, Any]] = []

    for raw_group in raw_duplicate_groups:
        if not isinstance(
            raw_group,
            Mapping,
        ):
            continue

        requirement_indexes = normalize_indexes(
            get_first_value(
                raw_group,
                "RequirementIndexes",
                "requirement_indexes",
                "SourceRequirementIndexes",
                "source_requirement_indexes",
                "Indexes",
                "indexes",
                default=[],
            ),
            total_requirements,
        )

        requirement_indexes = [
            index
            for index in requirement_indexes
            if index not in assigned_indexes
        ]

        if len(requirement_indexes) < 2:
            continue

        canonical_requirement = str(
            get_first_value(
                raw_group,
                "CanonicalRequirement",
                "canonical_requirement",
                "Canonical",
                "canonical",
                default="",
            )
            or ""
        ).strip()

        if not canonical_requirement:
            canonical_requirement = (
                get_requirement_text(
                    requirements[
                        requirement_indexes[0] - 1
                    ]
                )
            )

        reason = str(
            get_first_value(
                raw_group,
                "Reason",
                "reason",
                "Explanation",
                "explanation",
                default=(
                    "Requirements express the same "
                    "material obligation."
                ),
            )
            or ""
        ).strip()

        source_requirements = [
            requirements[index - 1]
            for index in requirement_indexes
        ]

        requirement_ids = [
            get_requirement_id(
                requirements[index - 1],
                index,
            )
            for index in requirement_indexes
        ]

        validated_groups.append(
            {
                "CanonicalRequirement": (
                    canonical_requirement
                ),
                "RequirementIndexes": (
                    requirement_indexes
                ),
                "RequirementIds": (
                    requirement_ids
                ),
                "SourceRequirements": (
                    source_requirements
                ),
                "DuplicateCount": len(
                    requirement_indexes
                ),
                "Reason": reason,
            }
        )

        assigned_indexes.update(
            requirement_indexes
        )

    requested_unique_indexes = normalize_indexes(
        get_first_value(
            result,
            "UniqueRequirementIndexes",
            "unique_requirement_indexes",
            "UniqueIndexes",
            "unique_indexes",
            default=[],
        ),
        total_requirements,
    )

    unique_indexes: list[int] = []

    for index in requested_unique_indexes:
        if (
            index not in assigned_indexes
            and index not in unique_indexes
        ):
            unique_indexes.append(index)

    # Any requirement omitted by the LLM becomes unique.
    for index in range(
        1,
        total_requirements + 1,
    ):
        if (
            index not in assigned_indexes
            and index not in unique_indexes
        ):
            unique_indexes.append(index)

    deduplicated_requirements: list[
        dict[str, Any]
    ] = []

    for group_number, group in enumerate(
        validated_groups,
        start=1,
    ):
        deduplicated_requirements.append(
            {
                "DeduplicatedRequirementId": (
                    f"DEDUP-GROUP-{group_number:04d}"
                ),
                "CanonicalRequirement": group[
                    "CanonicalRequirement"
                ],
                "RequirementIndexes": group[
                    "RequirementIndexes"
                ],
                "RequirementIds": group[
                    "RequirementIds"
                ],
                "SourceRequirements": group[
                    "SourceRequirements"
                ],
                "IsDuplicateGroup": True,
                "DuplicateCount": group[
                    "DuplicateCount"
                ],
            }
        )

    for index in unique_indexes:
        requirement = requirements[index - 1]

        deduplicated_requirements.append(
            {
                "DeduplicatedRequirementId": (
                    f"DEDUP-UNIQUE-{index:04d}"
                ),
                "CanonicalRequirement": (
                    get_requirement_text(
                        requirement
                    )
                ),
                "RequirementIndexes": [index],
                "RequirementIds": [
                    get_requirement_id(
                        requirement,
                        index,
                    )
                ],
                "SourceRequirements": [
                    requirement
                ],
                "IsDuplicateGroup": False,
                "DuplicateCount": 1,
            }
        )

    duplicates_removed = sum(
        group["DuplicateCount"] - 1
        for group in validated_groups
    )

    return {
        "Summary": {
            "TotalInputRequirements": (
                total_requirements
            ),
            "DuplicateGroupCount": len(
                validated_groups
            ),
            "UniqueRequirementCount": len(
                unique_indexes
            ),
            "DuplicatesRemoved": (
                duplicates_removed
            ),
            "TotalDeduplicatedRequirements": len(
                deduplicated_requirements
            ),
        },
        "DuplicateGroups": validated_groups,
        "UniqueRequirementIndexes": (
            unique_indexes
        ),
        "DeduplicatedRequirements": (
            deduplicated_requirements
        ),
    }


def extract_deduplication_result(
    final_state: Mapping[str, Any] | Any,
) -> dict[str, Any]:
    """
    Extract the final validated result from LangGraph.
    """

    if not isinstance(
        final_state,
        Mapping,
    ):
        raise ValueError(
            "LangGraph returned an invalid final state"
        )

    error = final_state.get("error")

    if error:
        raise RuntimeError(str(error))

    result = final_state.get("result")

    if not isinstance(result, Mapping):
        raise ValueError(
            "LangGraph completed without a valid "
            "deduplication result"
        )

    return dict(result)