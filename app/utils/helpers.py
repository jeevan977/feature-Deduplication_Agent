

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


def get_requirement_type(
    requirement: Any,
) -> str:
    """
    Return the requirement type without copying the complete source
    requirement into the Agent 1 output.
    """

    if not isinstance(requirement, Mapping):
        return ""

    for key in (
        "RequirementType",
        "requirement_type",
        "requirementType",
        "Type",
        "type",
    ):
        value = requirement.get(key)

        if value is None:
            continue

        requirement_type = str(value).strip()

        if requirement_type:
            return requirement_type

    return ""


def get_group_requirement_type(
    source_requirements: Sequence[Any],
) -> str:
    """
    Select a compact requirement type for a duplicate group.

    Semantically duplicated requirements should normally have the
    same type. When types differ, preserve the first non-empty type
    because Agent 2 does not require the full source-type history.
    """

    for requirement in source_requirements:
        requirement_type = get_requirement_type(
            requirement
        )

        if requirement_type:
            return requirement_type

    return ""


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
    Build the requirement-deduplication prompt.

    Only these requirement fields are sent to the LLM:

        RequirementId
        RequirementText
        RequirementType

    The complete original MongoDB requirement objects remain
    available in raw_requirements and are restored into the final
    validated output after the LLM response is processed.
    """

    del context

    requirements = normalize_requirements(
        raw_requirements
    )

    if not requirements:
        raise ValueError(
            "Cannot build prompt because no requirements "
            "were supplied"
        )

    llm_requirements: list[
        dict[str, str]
    ] = []

    for index, requirement in enumerate(
        requirements,
        start=1,
    ):
        requirement_id = get_requirement_id(
            requirement,
            index,
        )

        requirement_text = get_requirement_text(
            requirement
        )

        requirement_type = ""

        if isinstance(requirement, Mapping):
            requirement_type = str(
                requirement.get(
                    "RequirementType",
                    requirement.get(
                        "requirement_type",
                        "",
                    ),
                )
                or ""
            ).strip()

        llm_requirements.append(
            {
                "RequirementId": requirement_id,
                "RequirementText": requirement_text,
                "RequirementType": requirement_type,
            }
        )

    requirements_json = json.dumps(
        llm_requirements,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )

    prompt = f"""
You are a Requirement Deduplication Agent for tender and procurement requirements.

Compare requirements using only:

- RequirementId
- RequirementText
- RequirementType

RequirementId is used only for traceability.
Determine duplication mainly from RequirementText while considering
RequirementType where it materially changes the obligation.

A requirement is a duplicate only when satisfying one requirement would
substantially satisfy the other requirement.

Rules:

1. Do not mark requirements as duplicates only because they contain
   similar keywords or belong to the same broad topic.

2. Preserve materially different scope, quantities, dates, locations,
   standards, service levels, exclusions and compliance conditions.

3. Requirements with materially different conditions must remain separate.

4. Every supplied RequirementId must appear exactly once.

5. Every RequirementId must appear either inside one duplicate group
   or inside UniqueRequirementIds.

6. A duplicate group must contain at least two different RequirementIds.

7. Use only RequirementIds supplied in the input.

8. Return valid JSON only.

9. Do not return markdown or code fences.

Requirements:

{requirements_json}

Return exactly this JSON structure:

{{
  "DuplicateGroups": [
    {{
      "CanonicalRequirement": "Complete consolidated requirement",
      "RequirementIds": [
        "REQUIREMENT-ID-1",
        "REQUIREMENT-ID-2"
      ],
      "Reason": "Why these requirements express the same material obligation"
    }}
  ],
  "UniqueRequirementIds": [
    "REQUIREMENT-ID-3"
  ]
}}
""".strip()

    print(
        "Deduplication prompt prepared:",
        {
            "requirementCount": len(
                llm_requirements
            ),
            "characterCount": len(prompt),
            "estimatedTokenCount": round(
                len(prompt) / 4
            ),
            "fieldsSentToLlm": [
                "RequirementId",
                "RequirementText",
                "RequirementType",
            ],
            "fullOriginalObjectsIncluded": False,
            "contextIncluded": False,
        },
    )

    return prompt


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


def normalize_requirement_ids(
    value: Any,
    valid_requirement_ids: set[str],
) -> list[str]:
    """
    Normalize RequirementIds returned by the LLM.

    Unknown IDs are ignored and duplicates are removed while
    preserving the original response order.
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

    normalized_ids: list[str] = []

    for item in value:
        requirement_id = str(
            item or ""
        ).strip()

        if not requirement_id:
            continue

        if requirement_id not in valid_requirement_ids:
            continue

        if requirement_id in normalized_ids:
            continue

        normalized_ids.append(
            requirement_id
        )

    return normalized_ids


def normalize_output_string_list(
    value: Any,
) -> list[str]:
    """
    Normalize intent values while preserving the original display
    text and removing case-insensitive duplicates.
    """

    if value is None:
        return []

    if isinstance(value, str):
        values: Sequence[Any] = [value]

    elif isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        values = value

    else:
        values = [value]

    normalized_values: list[str] = []
    seen: set[str] = set()

    for item in values:
        item_text = str(item or "").strip()

        if not item_text:
            continue

        normalized_key = item_text.casefold()

        if normalized_key in seen:
            continue

        seen.add(normalized_key)
        normalized_values.append(item_text)

    return normalized_values


def collect_requirement_intent_values(
    source_requirements: Sequence[Any],
) -> dict[str, list[str]]:
    """
    Collect and merge Agent 1 intent metadata from all source
    requirements represented by one deduplicated requirement.

    For duplicate groups, values from every source requirement are
    merged and de-duplicated.

    These values are not sent to the Agent 1 LLM. They are restored
    from the original MongoDB requirements after the LLM returns its
    duplicate grouping decision.
    """

    capability_intents: list[str] = []
    evidence_sections: list[str] = []
    semantic_anchors: list[str] = []

    for source_requirement in source_requirements:
        if not isinstance(source_requirement, Mapping):
            continue

        # Support intent values already stored directly.
        capability_intents.extend(
            normalize_output_string_list(
                get_first_value(
                    source_requirement,
                    "CapabilityIntent",
                    "capability_intent",
                    "capabilityIntent",
                    default=[],
                )
            )
        )

        evidence_sections.extend(
            normalize_output_string_list(
                get_first_value(
                    source_requirement,
                    "EvidenceSections",
                    "evidence_sections",
                    "evidenceSections",
                    default=[],
                )
            )
        )

        semantic_anchors.extend(
            normalize_output_string_list(
                get_first_value(
                    source_requirement,
                    "SemanticAnchors",
                    "semantic_anchors",
                    "semanticAnchors",
                    default=[],
                )
            )
        )

        # Main current source: IntentResult from requirement extraction.
        intent_result = get_first_value(
            source_requirement,
            "IntentResult",
            "intentResult",
            "intent_result",
            default=None,
        )

        if not isinstance(intent_result, Mapping):
            continue

        capability_intents.extend(
            normalize_output_string_list(
                get_first_value(
                    intent_result,
                    "CapabilityIntent",
                    "capability_intent",
                    "capabilityIntent",
                    default=[],
                )
            )
        )

        evidence_sections.extend(
            normalize_output_string_list(
                get_first_value(
                    intent_result,
                    "EvidenceSections",
                    "evidence_sections",
                    "evidenceSections",
                    default=[],
                )
            )
        )

        semantic_anchors.extend(
            normalize_output_string_list(
                get_first_value(
                    intent_result,
                    "SemanticAnchors",
                    "semantic_anchors",
                    "semanticAnchors",
                    default=[],
                )
            )
        )

    return {
        "CapabilityIntent": (
            normalize_output_string_list(
                capability_intents
            )
        ),
        "EvidenceSections": (
            normalize_output_string_list(
                evidence_sections
            )
        ),
        "SemanticAnchors": (
            normalize_output_string_list(
                semantic_anchors
            )
        ),
    }


def validate_deduplication_result(
    result: Any,
    raw_requirements: Any,
) -> dict[str, Any]:
    """
    Validate and normalize the LLM deduplication result.

    The preferred LLM response uses RequirementIds. The previous
    RequirementIndexes format is also accepted for compatibility.

    Complete original requirement objects are restored from
    raw_requirements and are never required in the LLM response.
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

    requirement_id_to_index: dict[
        str,
        int,
    ] = {}

    requirement_index_to_id: dict[
        int,
        str,
    ] = {}

    for index, requirement in enumerate(
        requirements,
        start=1,
    ):
        requirement_id = get_requirement_id(
            requirement,
            index,
        )

        if requirement_id not in requirement_id_to_index:
            requirement_id_to_index[
                requirement_id
            ] = index

        requirement_index_to_id[
            index
        ] = requirement_id

    valid_requirement_ids = set(
        requirement_id_to_index.keys()
    )

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
    validated_groups: list[
        dict[str, Any]
    ] = []

    for raw_group in raw_duplicate_groups:
        if not isinstance(
            raw_group,
            Mapping,
        ):
            continue

        requirement_ids = (
            normalize_requirement_ids(
                get_first_value(
                    raw_group,
                    "RequirementIds",
                    "requirement_ids",
                    "SourceRequirementIds",
                    "source_requirement_ids",
                    default=[],
                ),
                valid_requirement_ids,
            )
        )

        requirement_indexes = [
            requirement_id_to_index[
                requirement_id
            ]
            for requirement_id in requirement_ids
        ]

        if not requirement_indexes:
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

            requirement_ids = [
                requirement_index_to_id[
                    index
                ]
                for index in requirement_indexes
            ]

        filtered_indexes: list[int] = []
        filtered_ids: list[str] = []

        for requirement_index, requirement_id in zip(
            requirement_indexes,
            requirement_ids,
        ):
            if requirement_index in assigned_indexes:
                continue

            if requirement_index in filtered_indexes:
                continue

            filtered_indexes.append(
                requirement_index
            )
            filtered_ids.append(
                requirement_id
            )

        requirement_indexes = filtered_indexes
        requirement_ids = filtered_ids

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
            canonical_requirement = get_requirement_text(
                requirements[
                    requirement_indexes[0] - 1
                ]
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

        intent_values = (
            collect_requirement_intent_values(
                source_requirements
            )
        )

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
                "CapabilityIntent": (
                    intent_values[
                        "CapabilityIntent"
                    ]
                ),
                "EvidenceSections": (
                    intent_values[
                        "EvidenceSections"
                    ]
                ),
                "SemanticAnchors": (
                    intent_values[
                        "SemanticAnchors"
                    ]
                ),
                "IntentResult": intent_values,
                "Reason": reason,
            }
        )

        assigned_indexes.update(
            requirement_indexes
        )

    requested_unique_ids = (
        normalize_requirement_ids(
            get_first_value(
                result,
                "UniqueRequirementIds",
                "unique_requirement_ids",
                "UniqueIds",
                "unique_ids",
                default=[],
            ),
            valid_requirement_ids,
        )
    )

    requested_unique_indexes = [
        requirement_id_to_index[
            requirement_id
        ]
        for requirement_id in requested_unique_ids
    ]

    if not requested_unique_indexes:
        requested_unique_indexes = (
            normalize_indexes(
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
        )

    unique_indexes: list[int] = []

    for index in requested_unique_indexes:
        if (
            index not in assigned_indexes
            and index not in unique_indexes
        ):
            unique_indexes.append(index)

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

    # --------------------------------------------------------------
    # Duplicate groups
    # --------------------------------------------------------------

    for group_number, group in enumerate(
        validated_groups,
        start=1,
    ):
        source_requirements = group.get(
            "SourceRequirements",
            [],
        )

        deduplicated_requirements.append(
            {
                "DeduplicatedRequirementId": (
                    f"DEDUP-GROUP-{group_number:04d}"
                ),
                "CanonicalRequirement": group[
                    "CanonicalRequirement"
                ],
                "RequirementIds": group[
                    "RequirementIds"
                ],
                "RequirementType": (
                    get_group_requirement_type(
                        source_requirements
                    )
                ),
                "IntentResult": {
                    "CapabilityIntent": (
                        group.get(
                            "CapabilityIntent",
                            [],
                        )
                    ),
                    "EvidenceSections": (
                        group.get(
                            "EvidenceSections",
                            [],
                        )
                    ),
                    "SemanticAnchors": (
                        group.get(
                            "SemanticAnchors",
                            [],
                        )
                    ),
                },
            }
        )

    # --------------------------------------------------------------
    # Unique requirements
    # --------------------------------------------------------------

    unique_output_number = 1

    for index in unique_indexes:
        requirement = requirements[index - 1]

        intent_values = (
            collect_requirement_intent_values(
                [requirement]
            )
        )

        deduplicated_requirements.append(
            {
                "DeduplicatedRequirementId": (
                    f"DEDUP-UNIQUE-"
                    f"{unique_output_number:04d}"
                ),
                "CanonicalRequirement": (
                    get_requirement_text(
                        requirement
                    )
                ),
                "RequirementIds": [
                    get_requirement_id(
                        requirement,
                        index,
                    )
                ],
                "RequirementType": (
                    get_requirement_type(
                        requirement
                    )
                ),
                "IntentResult": {
                    "CapabilityIntent": (
                        intent_values[
                            "CapabilityIntent"
                        ]
                    ),
                    "EvidenceSections": (
                        intent_values[
                            "EvidenceSections"
                        ]
                    ),
                    "SemanticAnchors": (
                        intent_values[
                            "SemanticAnchors"
                        ]
                    ),
                },
            }
        )

        unique_output_number += 1

    duplicates_removed = sum(
        group["DuplicateCount"] - 1
        for group in validated_groups
    )

    # This is the only result returned to service.py.
    # It intentionally excludes:
    #
    # - SourceRequirements
    # - RequirementIndexes
    # - DuplicateGroups
    # - UniqueRequirementIndexes
    # - UniqueRequirementIds
    # - complete source MongoDB documents

    return {
        "Summary": {
            "TotalInputRequirements": (
                total_requirements
            ),
            "TotalDeduplicatedRequirements": len(
                deduplicated_requirements
            ),
            "DuplicatesRemoved": (
                duplicates_removed
            ),
        },
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