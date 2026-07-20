

# from __future__ import annotations

# import json
# import re
# from dataclasses import asdict, is_dataclass
# from typing import Any, Mapping, Sequence, Optional
# from app.agents.Deduplication_Agent.graph.agent_state import (
#     DeduplicationState,
# )


# def convert_to_plain_value(value: Any) -> Any:
#     """
#     Convert Pydantic models, dataclasses and other values
#     into normal Python dictionaries and lists.
#     """

#     if hasattr(value, "model_dump"):
#         return value.model_dump(mode="python")

#     if is_dataclass(value):
#         return asdict(value)

#     if isinstance(value, Mapping):
#         return {
#             str(key): convert_to_plain_value(item)
#             for key, item in value.items()
#         }

#     if isinstance(value, Sequence) and not isinstance(
#         value,
#         (str, bytes, bytearray),
#     ):
#         return [
#             convert_to_plain_value(item)
#             for item in value
#         ]

#     return value


# def normalize_requirements(
#     raw_requirements: Any,
# ) -> list[Any]:
#     """
#     Convert requirement input into a normal list.
#     """

#     raw_requirements = convert_to_plain_value(
#         raw_requirements
#     )

#     if raw_requirements is None:
#         return []

#     if isinstance(raw_requirements, str):
#         requirement_text = raw_requirements.strip()

#         if not requirement_text:
#             return []

#         return [requirement_text]

#     if isinstance(raw_requirements, Mapping):
#         possible_keys = (
#             "RawRequirements",
#             "raw_requirements",
#             "Requirements",
#             "requirements",
#             "Items",
#             "items",
#         )

#         for key in possible_keys:
#             value = raw_requirements.get(key)

#             if value is not None:
#                 return normalize_requirements(value)

#         return [dict(raw_requirements)]

#     if isinstance(raw_requirements, Sequence) and not isinstance(
#         raw_requirements,
#         (str, bytes, bytearray),
#     ):
#         return [
#             item
#             for item in list(raw_requirements)
#             if item is not None and item != ""
#         ]

#     return [raw_requirements]


# def get_requirement_text(
#     requirement: Any,
# ) -> str:
#     """
#     Extract readable requirement text from different
#     possible requirement object structures.
#     """

#     if isinstance(requirement, str):
#         return requirement.strip()

#     if isinstance(requirement, Mapping):
#         possible_text_keys = (
#             "RequirementText",
#             "requirement_text",
#             "Text",
#             "text",
#             "Requirement",
#             "requirement",
#             "Description",
#             "description",
#             "Content",
#             "content",
#         )

#         for key in possible_text_keys:
#             value = requirement.get(key)

#             if value is not None:
#                 text = str(value).strip()

#                 if text:
#                     return text

#     return json.dumps(
#         requirement,
#         ensure_ascii=False,
#         default=str,
#         sort_keys=True,
#     )


# def get_requirement_id(
#     requirement: Any,
#     index: int,
# ) -> str:
#     """
#     Extract requirement ID. Create a temporary ID
#     when the input does not contain one.
#     """

#     if isinstance(requirement, Mapping):
#         possible_id_keys = (
#             "RequirementId",
#             "requirement_id",
#             "Id",
#             "id",
#             "_id",
#         )

#         for key in possible_id_keys:
#             value = requirement.get(key)

#             if value is not None:
#                 requirement_id = str(value).strip()

#                 if requirement_id:
#                     return requirement_id

#     return f"REQ-{index:04d}"


# def get_requirement_type(
#     requirement: Any,
# ) -> str:
#     """
#     Return the requirement type without copying the complete source
#     requirement into the Agent 1 output.
#     """

#     if not isinstance(requirement, Mapping):
#         return ""

#     for key in (
#         "RequirementType",
#         "requirement_type",
#         "requirementType",
#         "Type",
#         "type",
#     ):
#         value = requirement.get(key)

#         if value is None:
#             continue

#         requirement_type = str(value).strip()

#         if requirement_type:
#             return requirement_type

#     return ""


# def get_group_requirement_type(
#     source_requirements: Sequence[Any],
# ) -> str:
#     """
#     Select a compact requirement type for a duplicate group.

#     Semantically duplicated requirements should normally have the
#     same type. When types differ, preserve the first non-empty type
#     because Agent 2 does not require the full source-type history.
#     """

#     for requirement in source_requirements:
#         requirement_type = get_requirement_type(
#             requirement
#         )

#         if requirement_type:
#             return requirement_type

#     return ""


# def build_initial_state(
#     raw_requirements: Any,
#     context: Mapping[str, Any] | None = None,
#     bearer_token: str | None = None,
#     correlation_id: str | None = None,
# ) -> DeduplicationState:
#     """
#     Create the initial LangGraph state.
#     """

#     requirements = normalize_requirements(
#         raw_requirements
#     )

#     if not requirements:
#         raise ValueError(
#             "raw_requirements cannot be empty"
#         )

#     return DeduplicationState(
#         raw_requirements=requirements,
#         context=dict(context or {}),
#         bearer_token=bearer_token,
#         correlation_id=correlation_id,
#         prompt="",
#         llm_response=None,
#         result={},
#         error=None,
#     )


# def build_deduplication_prompt(
#     raw_requirements: Any,
#     context: Mapping[str, Any] | None = None,
# ) -> str:
#     """
#     Build the requirement-deduplication prompt.

#     Only these requirement fields are sent to the LLM:

#         RequirementId
#         RequirementText
#         RequirementType

#     The complete original MongoDB requirement objects remain
#     available in raw_requirements and are restored into the final
#     validated output after the LLM response is processed.
#     """

#     del context

#     requirements = normalize_requirements(
#         raw_requirements
#     )

#     if not requirements:
#         raise ValueError(
#             "Cannot build prompt because no requirements "
#             "were supplied"
#         )

#     llm_requirements: list[
#         dict[str, str]
#     ] = []

#     for index, requirement in enumerate(
#         requirements,
#         start=1,
#     ):
#         requirement_id = get_requirement_id(
#             requirement,
#             index,
#         )

#         requirement_text = get_requirement_text(
#             requirement
#         )

#         requirement_type = ""

#         if isinstance(requirement, Mapping):
#             requirement_type = str(
#                 requirement.get(
#                     "RequirementType",
#                     requirement.get(
#                         "requirement_type",
#                         "",
#                     ),
#                 )
#                 or ""
#             ).strip()

#         llm_requirements.append(
#             {
#                 "RequirementId": requirement_id,
#                 "RequirementText": requirement_text,
#                 "RequirementType": requirement_type,
#             }
#         )

#     requirements_json = json.dumps(
#         llm_requirements,
#         ensure_ascii=False,
#         default=str,
#         separators=(",", ":"),
#     )

#     prompt = f"""
# You are a Requirement Deduplication Agent for tender and procurement requirements.

# Compare requirements using only:

# - RequirementId
# - RequirementText
# - RequirementType

# RequirementId is used only for traceability.
# Determine duplication mainly from RequirementText while considering
# RequirementType where it materially changes the obligation.

# A requirement is a duplicate only when satisfying one requirement would
# substantially satisfy the other requirement.

# Rules:

# 1. Do not mark requirements as duplicates only because they contain
#    similar keywords or belong to the same broad topic.

# 2. Preserve materially different scope, quantities, dates, locations,
#    standards, service levels, exclusions and compliance conditions.

# 3. Requirements with materially different conditions must remain separate.

# 4. Every supplied RequirementId must appear exactly once.

# 5. Every RequirementId must appear either inside one duplicate group
#    or inside UniqueRequirementIds.

# 6. A duplicate group must contain at least two different RequirementIds.

# 7. Use only RequirementIds supplied in the input.

# 8. Return valid JSON only.

# 9. Do not return markdown or code fences.

# Requirements:

# {requirements_json}

# Return exactly this JSON structure:

# {{
#   "DuplicateGroups": [
#     {{
#       "CanonicalRequirement": "Complete consolidated requirement",
#       "RequirementIds": [
#         "REQUIREMENT-ID-1",
#         "REQUIREMENT-ID-2"
#       ],
#       "Reason": "Why these requirements express the same material obligation"
#     }}
#   ],
#   "UniqueRequirementIds": [
#     "REQUIREMENT-ID-3"
#   ]
# }}
# """.strip()

#     print(
#         "Deduplication prompt prepared:",
#         {
#             "requirementCount": len(
#                 llm_requirements
#             ),
#             "characterCount": len(prompt),
#             "estimatedTokenCount": round(
#                 len(prompt) / 4
#             ),
#             "fieldsSentToLlm": [
#                 "RequirementId",
#                 "RequirementText",
#                 "RequirementType",
#             ],
#             "fullOriginalObjectsIncluded": False,
#             "contextIncluded": False,
#         },
#     )

#     return prompt


# def extract_response_content(
#     llm_response: Any,
# ) -> Any:
#     """
#     Extract response content from LangChain messages
#     and normal response objects.
#     """

#     if llm_response is None:
#         raise ValueError(
#             "LLM returned no response"
#         )

#     if isinstance(
#         llm_response,
#         (dict, list),
#     ):
#         return llm_response

#     content = getattr(
#         llm_response,
#         "content",
#         None,
#     )

#     if content is not None:
#         if isinstance(content, list):
#             text_parts: list[str] = []

#             for part in content:
#                 if isinstance(part, str):
#                     text_parts.append(part)

#                 elif isinstance(part, Mapping):
#                     text = (
#                         part.get("text")
#                         or part.get("content")
#                     )

#                     if text is not None:
#                         text_parts.append(str(text))

#             return "\n".join(text_parts)

#         return content

#     return str(llm_response)


# def remove_markdown_code_fence(
#     text: str,
# ) -> str:
#     """
#     Remove ```json code fences from an LLM response.
#     """

#     text = text.strip()

#     fenced_match = re.fullmatch(
#         r"```(?:json)?\s*(.*?)\s*```",
#         text,
#         flags=re.IGNORECASE | re.DOTALL,
#     )

#     if fenced_match:
#         return fenced_match.group(1).strip()

#     return text


# def decode_json_response(
#     text: str,
# ) -> Any:
#     """
#     Decode JSON even when the model accidentally adds
#     some text before or after the JSON object.
#     """

#     text = remove_markdown_code_fence(text)

#     try:
#         return json.loads(text)

#     except json.JSONDecodeError:
#         pass

#     decoder = json.JSONDecoder()

#     for position, character in enumerate(text):
#         if character not in "[{":
#             continue

#         try:
#             parsed_value, _ = decoder.raw_decode(
#                 text[position:]
#             )

#             return parsed_value

#         except json.JSONDecodeError:
#             continue

#     raise ValueError(
#         "LLM response did not contain valid JSON. "
#         f"Response preview: {text[:500]}"
#     )


# def parse_llm_response(
#     llm_response: Any,
# ) -> dict[str, Any]:
#     """
#     Convert the LLM response into a Python dictionary.
#     """

#     content = extract_response_content(
#         llm_response
#     )

#     if isinstance(content, Mapping):
#         parsed_result = dict(content)

#     elif isinstance(content, list):
#         parsed_result = {
#             "DuplicateGroups": content
#         }

#     else:
#         decoded_value = decode_json_response(
#             str(content)
#         )

#         if not isinstance(
#             decoded_value,
#             Mapping,
#         ):
#             raise ValueError(
#                 "LLM JSON response must be an object"
#             )

#         parsed_result = dict(decoded_value)

#     possible_wrapper_keys = (
#         "result",
#         "Result",
#         "output",
#         "Output",
#         "data",
#         "Data",
#     )

#     for wrapper_key in possible_wrapper_keys:
#         wrapped_result = parsed_result.get(
#             wrapper_key
#         )

#         if isinstance(
#             wrapped_result,
#             Mapping,
#         ):
#             parsed_result = dict(
#                 wrapped_result
#             )
#             break

#     return parsed_result


# def get_first_value(
#     mapping: Mapping[str, Any],
#     *keys: str,
#     default: Any = None,
# ) -> Any:
#     """
#     Get the first available value using multiple
#     possible property names.
#     """

#     for key in keys:
#         if key in mapping:
#             return mapping[key]

#     return default


# def normalize_indexes(
#     value: Any,
#     total_requirements: int,
# ) -> list[int]:
#     """
#     Convert LLM indexes into a valid unique list.
#     """

#     if value is None:
#         return []

#     if not isinstance(
#         value,
#         Sequence,
#     ) or isinstance(
#         value,
#         (str, bytes, bytearray),
#     ):
#         value = [value]

#     indexes: list[int] = []

#     for item in value:
#         try:
#             index = int(item)

#         except (TypeError, ValueError):
#             continue

#         if (
#             1 <= index <= total_requirements
#             and index not in indexes
#         ):
#             indexes.append(index)

#     return indexes


# def normalize_requirement_ids(
#     value: Any,
#     valid_requirement_ids: set[str],
# ) -> list[str]:
#     """
#     Normalize RequirementIds returned by the LLM.

#     Unknown IDs are ignored and duplicates are removed while
#     preserving the original response order.
#     """

#     if value is None:
#         return []

#     if not isinstance(
#         value,
#         Sequence,
#     ) or isinstance(
#         value,
#         (str, bytes, bytearray),
#     ):
#         value = [value]

#     normalized_ids: list[str] = []

#     for item in value:
#         requirement_id = str(
#             item or ""
#         ).strip()

#         if not requirement_id:
#             continue

#         if requirement_id not in valid_requirement_ids:
#             continue

#         if requirement_id in normalized_ids:
#             continue

#         normalized_ids.append(
#             requirement_id
#         )

#     return normalized_ids


# def normalize_output_string_list(
#     value: Any,
# ) -> list[str]:
#     """
#     Normalize intent values while preserving the original display
#     text and removing case-insensitive duplicates.
#     """

#     if value is None:
#         return []

#     if isinstance(value, str):
#         values: Sequence[Any] = [value]

#     elif isinstance(value, Sequence) and not isinstance(
#         value,
#         (str, bytes, bytearray),
#     ):
#         values = value

#     else:
#         values = [value]

#     normalized_values: list[str] = []
#     seen: set[str] = set()

#     for item in values:
#         item_text = str(item or "").strip()

#         if not item_text:
#             continue

#         normalized_key = item_text.casefold()

#         if normalized_key in seen:
#             continue

#         seen.add(normalized_key)
#         normalized_values.append(item_text)

#     return normalized_values


# def collect_requirement_intent_values(
#     source_requirements: Sequence[Any],
# ) -> dict[str, list[str]]:
#     """
#     Collect and merge Agent 1 intent metadata from all source
#     requirements represented by one deduplicated requirement.

#     For duplicate groups, values from every source requirement are
#     merged and de-duplicated.

#     These values are not sent to the Agent 1 LLM. They are restored
#     from the original MongoDB requirements after the LLM returns its
#     duplicate grouping decision.
#     """

#     capability_intents: list[str] = []
#     evidence_sections: list[str] = []
#     semantic_anchors: list[str] = []

#     for source_requirement in source_requirements:
#         if not isinstance(source_requirement, Mapping):
#             continue

#         # Support intent values already stored directly.
#         capability_intents.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     source_requirement,
#                     "CapabilityIntent",
#                     "capability_intent",
#                     "capabilityIntent",
#                     default=[],
#                 )
#             )
#         )

#         evidence_sections.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     source_requirement,
#                     "EvidenceSections",
#                     "evidence_sections",
#                     "evidenceSections",
#                     default=[],
#                 )
#             )
#         )

#         semantic_anchors.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     source_requirement,
#                     "SemanticAnchors",
#                     "semantic_anchors",
#                     "semanticAnchors",
#                     default=[],
#                 )
#             )
#         )

#         # Main current source: IntentResult from requirement extraction.
#         intent_result = get_first_value(
#             source_requirement,
#             "IntentResult",
#             "intentResult",
#             "intent_result",
#             default=None,
#         )

#         if not isinstance(intent_result, Mapping):
#             continue

#         capability_intents.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     intent_result,
#                     "CapabilityIntent",
#                     "capability_intent",
#                     "capabilityIntent",
#                     default=[],
#                 )
#             )
#         )

#         evidence_sections.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     intent_result,
#                     "EvidenceSections",
#                     "evidence_sections",
#                     "evidenceSections",
#                     default=[],
#                 )
#             )
#         )

#         semantic_anchors.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     intent_result,
#                     "SemanticAnchors",
#                     "semantic_anchors",
#                     "semanticAnchors",
#                     default=[],
#                 )
#             )
#         )

#     return {
#         "CapabilityIntent": (
#             normalize_output_string_list(
#                 capability_intents
#             )
#         ),
#         "EvidenceSections": (
#             normalize_output_string_list(
#                 evidence_sections
#             )
#         ),
#         "SemanticAnchors": (
#             normalize_output_string_list(
#                 semantic_anchors
#             )
#         ),
#     }


# def normalize_output_string_list(
#     value: Any,
# ) -> list[str]:
#     """
#     Convert a value into a clean list of strings.

#     Empty values are removed and duplicate values are removed
#     case-insensitively while preserving the original order.
#     """

#     if value is None:
#         return []

#     if isinstance(value, str):
#         values: Sequence[Any] = [value]

#     elif (
#         isinstance(value, Sequence)
#         and not isinstance(
#             value,
#             (
#                 str,
#                 bytes,
#                 bytearray,
#             ),
#         )
#     ):
#         values = value

#     else:
#         values = [value]

#     normalized_values: list[str] = []
#     seen_values: set[str] = set()

#     for item in values:
#         item_text = str(
#             item or ""
#         ).strip()

#         if not item_text:
#             continue

#         normalized_key = (
#             item_text.casefold()
#         )

#         if normalized_key in seen_values:
#             continue

#         seen_values.add(
#             normalized_key
#         )

#         normalized_values.append(
#             item_text
#         )

#     return normalized_values


# def collect_requirement_intent_values(
#     source_requirements: Sequence[Any],
# ) -> dict[str, list[str]]:
#     """
#     Collect CapabilityIntent, EvidenceSections and SemanticAnchors
#     from all original requirements represented by one deduplicated
#     requirement.

#     The function supports both direct fields and fields stored inside
#     IntentResult. It also supports common nested MongoDB wrappers such
#     as Document, Requirement, Payload and Data.
#     """

#     capability_intents: list[str] = []
#     evidence_sections: list[str] = []
#     semantic_anchors: list[str] = []

#     def collect_from_mapping(
#         mapping: Mapping[str, Any],
#         depth: int = 0,
#     ) -> None:
#         """
#         Read intent values from one mapping and selected nested
#         mappings.
#         """

#         if depth > 4:
#             return

#         # --------------------------------------------------------
#         # Read fields stored directly on the requirement
#         # --------------------------------------------------------

#         capability_intents.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     mapping,
#                     "CapabilityIntent",
#                     "capability_intent",
#                     "capabilityIntent",
#                     default=[],
#                 )
#             )
#         )

#         evidence_sections.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     mapping,
#                     "EvidenceSections",
#                     "evidence_sections",
#                     "evidenceSections",
#                     default=[],
#                 )
#             )
#         )

#         semantic_anchors.extend(
#             normalize_output_string_list(
#                 get_first_value(
#                     mapping,
#                     "SemanticAnchors",
#                     "semantic_anchors",
#                     "semanticAnchors",
#                     default=[],
#                 )
#             )
#         )

#         # --------------------------------------------------------
#         # Read fields stored inside IntentResult
#         # --------------------------------------------------------

#         intent_result = get_first_value(
#             mapping,
#             "IntentResult",
#             "intentResult",
#             "intent_result",
#             default=None,
#         )

#         if isinstance(
#             intent_result,
#             Mapping,
#         ):
#             capability_intents.extend(
#                 normalize_output_string_list(
#                     get_first_value(
#                         intent_result,
#                         "CapabilityIntent",
#                         "capability_intent",
#                         "capabilityIntent",
#                         default=[],
#                     )
#                 )
#             )

#             evidence_sections.extend(
#                 normalize_output_string_list(
#                     get_first_value(
#                         intent_result,
#                         "EvidenceSections",
#                         "evidence_sections",
#                         "evidenceSections",
#                         default=[],
#                     )
#                 )
#             )

#             semantic_anchors.extend(
#                 normalize_output_string_list(
#                     get_first_value(
#                         intent_result,
#                         "SemanticAnchors",
#                         "semantic_anchors",
#                         "semanticAnchors",
#                         default=[],
#                     )
#                 )
#             )

#         # --------------------------------------------------------
#         # Support common nested source-document structures
#         # --------------------------------------------------------

#         nested_mapping_keys = (
#             "Document",
#             "document",
#             "Requirement",
#             "requirement",
#             "SourceRequirement",
#             "sourceRequirement",
#             "Payload",
#             "payload",
#             "Data",
#             "data",
#             "Metadata",
#             "metadata",
#             "Item",
#             "item",
#         )

#         for nested_key in nested_mapping_keys:
#             nested_value = mapping.get(
#                 nested_key
#             )

#             if isinstance(
#                 nested_value,
#                 Mapping,
#             ):
#                 collect_from_mapping(
#                     nested_value,
#                     depth + 1,
#                 )

#     for source_requirement in source_requirements:
#         if not isinstance(
#             source_requirement,
#             Mapping,
#         ):
#             continue

#         collect_from_mapping(
#             source_requirement
#         )

#     return {
#         "CapabilityIntent": (
#             normalize_output_string_list(
#                 capability_intents
#             )
#         ),
#         "EvidenceSections": (
#             normalize_output_string_list(
#                 evidence_sections
#             )
#         ),
#         "SemanticAnchors": (
#             normalize_output_string_list(
#                 semantic_anchors
#             )
#         ),
#     }

# def validate_deduplication_result(
#     result: Any,
#     raw_requirements: Any,
# ) -> dict[str, Any]:
#     """
#     Validate and normalize the LLM deduplication result.

#     The preferred LLM response uses RequirementIds. The previous
#     RequirementIndexes format is also accepted for compatibility.

#     Complete original requirement objects are restored from
#     raw_requirements and are never required in the LLM response.
#     """

#     requirements = normalize_requirements(
#         raw_requirements
#     )

#     if not requirements:
#         raise ValueError(
#             "No raw requirements are available for validation"
#         )

#     if not isinstance(result, Mapping):
#         raise ValueError(
#             "Deduplication result must be a dictionary"
#         )

#     total_requirements = len(requirements)

#     requirement_id_to_index: dict[
#         str,
#         int,
#     ] = {}

#     requirement_index_to_id: dict[
#         int,
#         str,
#     ] = {}

#     for index, requirement in enumerate(
#         requirements,
#         start=1,
#     ):
#         requirement_id = get_requirement_id(
#             requirement,
#             index,
#         )

#         if requirement_id not in requirement_id_to_index:
#             requirement_id_to_index[
#                 requirement_id
#             ] = index

#         requirement_index_to_id[
#             index
#         ] = requirement_id

#     valid_requirement_ids = set(
#         requirement_id_to_index.keys()
#     )

#     raw_duplicate_groups = get_first_value(
#         result,
#         "DuplicateGroups",
#         "duplicate_groups",
#         "Groups",
#         "groups",
#         default=[],
#     )

#     if not isinstance(
#         raw_duplicate_groups,
#         Sequence,
#     ) or isinstance(
#         raw_duplicate_groups,
#         (str, bytes, bytearray),
#     ):
#         raw_duplicate_groups = []

#     assigned_indexes: set[int] = set()
#     validated_groups: list[
#         dict[str, Any]
#     ] = []

#     for raw_group in raw_duplicate_groups:
#         if not isinstance(
#             raw_group,
#             Mapping,
#         ):
#             continue

#         requirement_ids = (
#             normalize_requirement_ids(
#                 get_first_value(
#                     raw_group,
#                     "RequirementIds",
#                     "requirement_ids",
#                     "SourceRequirementIds",
#                     "source_requirement_ids",
#                     default=[],
#                 ),
#                 valid_requirement_ids,
#             )
#         )

#         requirement_indexes = [
#             requirement_id_to_index[
#                 requirement_id
#             ]
#             for requirement_id in requirement_ids
#         ]

#         if not requirement_indexes:
#             requirement_indexes = normalize_indexes(
#                 get_first_value(
#                     raw_group,
#                     "RequirementIndexes",
#                     "requirement_indexes",
#                     "SourceRequirementIndexes",
#                     "source_requirement_indexes",
#                     "Indexes",
#                     "indexes",
#                     default=[],
#                 ),
#                 total_requirements,
#             )

#             requirement_ids = [
#                 requirement_index_to_id[
#                     index
#                 ]
#                 for index in requirement_indexes
#             ]

#         filtered_indexes: list[int] = []
#         filtered_ids: list[str] = []

#         for requirement_index, requirement_id in zip(
#             requirement_indexes,
#             requirement_ids,
#         ):
#             if requirement_index in assigned_indexes:
#                 continue

#             if requirement_index in filtered_indexes:
#                 continue

#             filtered_indexes.append(
#                 requirement_index
#             )
#             filtered_ids.append(
#                 requirement_id
#             )

#         requirement_indexes = filtered_indexes
#         requirement_ids = filtered_ids

#         if len(requirement_indexes) < 2:
#             continue

#         canonical_requirement = str(
#             get_first_value(
#                 raw_group,
#                 "CanonicalRequirement",
#                 "canonical_requirement",
#                 "Canonical",
#                 "canonical",
#                 default="",
#             )
#             or ""
#         ).strip()

#         if not canonical_requirement:
#             canonical_requirement = get_requirement_text(
#                 requirements[
#                     requirement_indexes[0] - 1
#                 ]
#             )

#         reason = str(
#             get_first_value(
#                 raw_group,
#                 "Reason",
#                 "reason",
#                 "Explanation",
#                 "explanation",
#                 default=(
#                     "Requirements express the same "
#                     "material obligation."
#                 ),
#             )
#             or ""
#         ).strip()

#         source_requirements = [
#             requirements[index - 1]
#             for index in requirement_indexes
#         ]

#         intent_values = (
#             collect_requirement_intent_values(
#                 source_requirements
#             )
#         )

#         validated_groups.append(
#             {
#                 "CanonicalRequirement": (
#                     canonical_requirement
#                 ),
#                 "RequirementIndexes": (
#                     requirement_indexes
#                 ),
#                 "RequirementIds": (
#                     requirement_ids
#                 ),
#                 "SourceRequirements": (
#                     source_requirements
#                 ),
#                 "DuplicateCount": len(
#                     requirement_indexes
#                 ),
#                 "CapabilityIntent": (
#                     intent_values[
#                         "CapabilityIntent"
#                     ]
#                 ),
#                 "EvidenceSections": (
#                     intent_values[
#                         "EvidenceSections"
#                     ]
#                 ),
#                 "SemanticAnchors": (
#                     intent_values[
#                         "SemanticAnchors"
#                     ]
#                 ),
#                 "IntentResult": intent_values,
#                 "Reason": reason,
#             }
#         )

#         assigned_indexes.update(
#             requirement_indexes
#         )

#     requested_unique_ids = (
#         normalize_requirement_ids(
#             get_first_value(
#                 result,
#                 "UniqueRequirementIds",
#                 "unique_requirement_ids",
#                 "UniqueIds",
#                 "unique_ids",
#                 default=[],
#             ),
#             valid_requirement_ids,
#         )
#     )

#     requested_unique_indexes = [
#         requirement_id_to_index[
#             requirement_id
#         ]
#         for requirement_id in requested_unique_ids
#     ]

#     if not requested_unique_indexes:
#         requested_unique_indexes = (
#             normalize_indexes(
#                 get_first_value(
#                     result,
#                     "UniqueRequirementIndexes",
#                     "unique_requirement_indexes",
#                     "UniqueIndexes",
#                     "unique_indexes",
#                     default=[],
#                 ),
#                 total_requirements,
#             )
#         )

#     unique_indexes: list[int] = []

#     for index in requested_unique_indexes:
#         if (
#             index not in assigned_indexes
#             and index not in unique_indexes
#         ):
#             unique_indexes.append(index)

#     for index in range(
#         1,
#         total_requirements + 1,
#     ):
#         if (
#             index not in assigned_indexes
#             and index not in unique_indexes
#         ):
#             unique_indexes.append(index)

#     deduplicated_requirements: list[
#         dict[str, Any]
#     ] = []

#     # --------------------------------------------------------------
#     # Duplicate groups
#     # --------------------------------------------------------------

#     for group_number, group in enumerate(
#         validated_groups,
#         start=1,
#     ):
#         source_requirements = group.get(
#             "SourceRequirements",
#             [],
#         )



# # "CanonicalRequirementId": (
# #     f"CR{len(deduplicated_requirements) + 1}"
# # ),

#         deduplicated_requirements.append(
#             {
#                 "CanonicalRequirementId": (
#                     f"CR-{group_number:04d}"
#                 ),
#                 "CanonicalRequirement": group[
#                     "CanonicalRequirement"
#                 ],
#                 "RequirementIds": group[
#                     "RequirementIds"
#                 ],
#                 "RequirementType": (
#                     get_group_requirement_type(
#                         source_requirements
#                     )
#                 ),
#                 "IntentResult": {
#                     "CapabilityIntent": (
#                         group.get(
#                             "CapabilityIntent",
#                             [],
#                         )
#                     ),
#                     "EvidenceSections": (
#                         group.get(
#                             "EvidenceSections",
#                             [],
#                         )
#                     ),
#                     "SemanticAnchors": (
#                         group.get(
#                             "SemanticAnchors",
#                             [],
#                         )
#                     ),
#                 },
#             }
#         )

#     # --------------------------------------------------------------
#     # Unique requirements
#     # --------------------------------------------------------------

#     unique_output_number = 1

#     for index in unique_indexes:
#         requirement = requirements[index - 1]

#         intent_values = (
#             collect_requirement_intent_values(
#                 [requirement]
#             )
#         )

#         deduplicated_requirements.append(
#             {
#                 "CanonicalRequirementId": (
#                     f"DEDUP-UNIQUE-"
#                     f"{unique_output_number:04d}"
#                 ),
#                 "CanonicalRequirement": (
#                     get_requirement_text(
#                         requirement
#                     )
#                 ),
#                 "RequirementIds": [
#                     get_requirement_id(
#                         requirement,
#                         index,
#                     )
#                 ],
#                 "RequirementType": (
#                     get_requirement_type(
#                         requirement
#                     )
#                 ),
#                 "IntentResult": {
#                     "CapabilityIntent": (
#                         intent_values[
#                             "CapabilityIntent"
#                         ]
#                     ),
#                     "EvidenceSections": (
#                         intent_values[
#                             "EvidenceSections"
#                         ]
#                     ),
#                     "SemanticAnchors": (
#                         intent_values[
#                             "SemanticAnchors"
#                         ]
#                     ),
#                 },
#             }
#         )

#         unique_output_number += 1

#     duplicates_removed = sum(
#         group["DuplicateCount"] - 1
#         for group in validated_groups
#     )

#     # This is the only result returned to service.py.
#     # It intentionally excludes:
#     #
#     # - SourceRequirements
#     # - RequirementIndexes
#     # - DuplicateGroups
#     # - UniqueRequirementIndexes
#     # - UniqueRequirementIds
#     # - complete source MongoDB documents

#     return {
#         "Summary": {
#             "TotalInputRequirements": (
#                 total_requirements
#             ),
#             "TotalDeduplicatedRequirements": len(
#                 deduplicated_requirements
#             ),
#             "DuplicatesRemoved": (
#                 duplicates_removed
#             ),
#         },
#         "DeduplicatedRequirements": (
#             deduplicated_requirements
#         ),
#     }


# def extract_deduplication_result(
#     final_state: Mapping[str, Any] | Any,
# ) -> dict[str, Any]:
#     """
#     Extract the final validated result from LangGraph.
#     """

#     if not isinstance(
#         final_state,
#         Mapping,
#     ):
#         raise ValueError(
#             "LangGraph returned an invalid final state"
#         )

#     error = final_state.get("error")

#     if error:
#         raise RuntimeError(str(error))

#     result = final_state.get("result")

#     if not isinstance(result, Mapping):
#         raise ValueError(
#             "LangGraph completed without a valid "
#             "deduplication result"
#         )

#     return dict(result)


from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from difflib import SequenceMatcher
from typing import Any, Mapping, Sequence

from app.agents.Deduplication_Agent.graph.agent_state import (
    DeduplicationState,
)
from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------------------
# Generic input helpers
# ---------------------------------------------------------------------------

# ================================================================
# REQUIREMENT DEDUPLICATION INSTRUCTION FILES
# ================================================================

HELPERS_FILE_PATH = Path(__file__).resolve()

# helpers.py is located at:
# app/utils/helpers.py
#
# Therefore parents[1] resolves to:
# app/
APP_DIRECTORY = HELPERS_FILE_PATH.parents[1]

DEDUPLICATION_AGENT_DIRECTORY = (
    APP_DIRECTORY
    / "agents"
    / "Deduplication_Agent"
)

DEDUPLICATION_INPUT_FILES_DIRECTORY = (
    DEDUPLICATION_AGENT_DIRECTORY
    / "input_files"
)

DEDUPLICATION_CONSTITUTION_PATH = (
    DEDUPLICATION_INPUT_FILES_DIRECTORY
    / "Constitution.md"
)

DEDUPLICATION_SPECIFICATION_PATH = (
    DEDUPLICATION_INPUT_FILES_DIRECTORY
    / "Specification.md"
)


def convert_to_plain_value(value: Any) -> Any:
    """Convert Pydantic/dataclass values into plain Python values."""

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
    """Convert requirement input into one normal list."""

    raw_requirements = convert_to_plain_value(
        raw_requirements
    )

    if raw_requirements is None:
        return []

    if isinstance(raw_requirements, str):
        requirement_text = raw_requirements.strip()
        return [requirement_text] if requirement_text else []

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


def _find_nested_requirement_value(
    requirement: Any,
    keys: Sequence[str],
    *,
    max_depth: int = 4,
) -> Any:
    """Find a value at the top level or in common nested wrappers."""

    if max_depth < 0 or not isinstance(requirement, Mapping):
        return None

    for key in keys:
        value = requirement.get(key)

        if value is None:
            continue

        if isinstance(value, str):
            if value.strip():
                return value
        else:
            return value

    nested_keys = (
        "Document",
        "document",
        "Requirement",
        "requirement",
        "SourceRequirement",
        "sourceRequirement",
        "Payload",
        "payload",
        "Data",
        "data",
        "Metadata",
        "metadata",
        "Item",
        "item",
    )

    for nested_key in nested_keys:
        nested_value = requirement.get(nested_key)

        if isinstance(nested_value, Mapping):
            found_value = _find_nested_requirement_value(
                nested_value,
                keys,
                max_depth=max_depth - 1,
            )

            if found_value is not None:
                return found_value

    return None


def get_requirement_text(requirement: Any) -> str:
    """Extract readable requirement text."""

    if isinstance(requirement, str):
        return requirement.strip()

    value = _find_nested_requirement_value(
        requirement,
        (
            "RequirementText",
            "requirement_text",
            "requirementText",
            "Text",
            "text",
            "Description",
            "description",
            "Content",
            "content",
        ),
    )

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
    """Extract a source RequirementId or generate a temporary one."""

    value = _find_nested_requirement_value(
        requirement,
        (
            "RequirementId",
            "requirement_id",
            "requirementId",
            "Id",
            "id",
            "_id",
        ),
    )

    if value is not None:
        requirement_id = str(value).strip()

        if requirement_id:
            return requirement_id

    return f"REQ-{index:04d}"


def get_requirement_type(requirement: Any) -> str:
    """Extract RequirementType from top-level or nested data."""

    value = _find_nested_requirement_value(
        requirement,
        (
            "RequirementType",
            "requirement_type",
            "requirementType",
            "Type",
            "type",
        ),
    )

    return str(value or "").strip()


def build_initial_state(
    raw_requirements: Any,
    context: Mapping[str, Any] | None = None,
    bearer_token: str | None = None,
    correlation_id: str | None = None,
) -> DeduplicationState:
    """Create the initial LangGraph state."""

    requirements = normalize_requirements(raw_requirements)

    if not requirements:
        raise ValueError("raw_requirements cannot be empty")

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



@lru_cache(maxsize=4)
def read_required_deduplication_instruction_file(
    file_path: str,
) -> str:
    """
    Read one required Requirement Deduplication instruction file.

    The file content is cached so it is not read from disk for every
    API request.
    """

    resolved_path = Path(
        file_path
    ).resolve()

    if not resolved_path.is_file():
        raise FileNotFoundError(
            "Required Requirement Deduplication instruction file "
            f"was not found: {resolved_path}"
        )

    try:
        content = resolved_path.read_text(
            encoding="utf-8"
        ).strip()

    except UnicodeDecodeError as exc:
        raise ValueError(
            "Requirement Deduplication instruction file must use "
            f"UTF-8 encoding: {resolved_path}"
        ) from exc

    except OSError as exc:
        raise RuntimeError(
            "Unable to read Requirement Deduplication instruction "
            f"file: {resolved_path}. Error: {exc}"
        ) from exc

    if not content:
        raise ValueError(
            "Required Requirement Deduplication instruction file "
            f"is empty: {resolved_path}"
        )

    return content


@lru_cache(maxsize=1)
def load_deduplication_instructions() -> tuple[str, str]:
    """
    Load and cache the Requirement Deduplication Constitution and
    Specification files.

    Returns:
        tuple[str, str]:
            constitution content,
            specification content
    """

    constitution = (
        read_required_deduplication_instruction_file(
            str(
                DEDUPLICATION_CONSTITUTION_PATH
            )
        )
    )

    specification = (
        read_required_deduplication_instruction_file(
            str(
                DEDUPLICATION_SPECIFICATION_PATH
            )
        )
    )

    print(
        "Requirement Deduplication instruction files loaded:",
        {
            "constitutionPath": str(
                DEDUPLICATION_CONSTITUTION_PATH
            ),
            "specificationPath": str(
                DEDUPLICATION_SPECIFICATION_PATH
            ),
            "constitutionCharacters": len(
                constitution
            ),
            "specificationCharacters": len(
                specification
            ),
        },
    )

    return constitution, specification


# ---------------------------------------------------------------------------
# Prompt and LLM response parsing
# ---------------------------------------------------------------------------


# def build_deduplication_prompt(
#     raw_requirements: Any,
#     context: Mapping[str, Any] | None = None,
# ) -> str:
#     """
#     Build one compact one-go deduplication prompt.

#     Only RequirementId, RequirementText and RequirementType are sent
#     to the LLM. Original source objects remain in graph state.
#     """

#     del context

#     requirements = normalize_requirements(raw_requirements)

#     if not requirements:
#         raise ValueError(
#             "Cannot build prompt because no requirements were supplied"
#         )

#     llm_requirements: list[dict[str, str]] = []

#     for index, requirement in enumerate(requirements, start=1):
#         llm_requirements.append(
#             {
#                 "RequirementId": get_requirement_id(
#                     requirement,
#                     index,
#                 ),
#                 "RequirementText": get_requirement_text(
#                     requirement
#                 ),
#                 "RequirementType": get_requirement_type(
#                     requirement
#                 ),
#             }
#         )

#     requirements_json = json.dumps(
#         llm_requirements,
#         ensure_ascii=False,
#         default=str,
#         separators=(",", ":"),
#     )

#     prompt = f"""
# You are a Requirement Deduplication Agent for tender and procurement requirements.

# Compare all supplied requirements in one pass using only RequirementId,
# RequirementText and RequirementType. RequirementId is for traceability only.

# STRICT DECISION STANDARD

# Merge requirements only when they express the same complete material obligation
# and are interchangeable without changing the supplier's duty, trigger, scope,
# condition, exception, remedy, timeframe, quantity, threshold or deliverable.

# A false merge is more harmful than a missed duplicate. When uncertain, keep the
# requirements separate.

# RULES

# 1. Similar keywords, the same topic, the same customer, the same RequirementType,
#    or the same opening sentence do not make requirements duplicates.

# 2. Keep requirements separate when they differ in any material detail, including:
#    action, outcome, trigger, condition, exception, liability, remedy, timeframe,
#    quantity, percentage, date, location, standard, service level, clause reference,
#    evidence requirement, deliverable or responsible party.

# 3. A shared introductory clause followed by different conditions means separate
#    requirements.

# 4. Do not merge a general requirement with a specific requirement when the
#    specific requirement adds a separate obligation.

# 5. RequirementType may help interpretation, but it must not force a merge and it
#    must not prevent otherwise identical text from being merged.

# 6. A shortened extract may be a duplicate of a longer requirement only when the
#    shortened text contains the same complete obligation and adds no conflict.

# 7. For each duplicate group, CanonicalRequirement must be a complete standalone
#    requirement supported by every grouped source. Do not invent or combine
#    different obligations.

# 8. Every supplied RequirementId must appear exactly once: either in one
#    DuplicateGroups item or in UniqueRequirementIds.

# 9. A duplicate group must contain at least two different supplied RequirementIds.

# 10. Use only supplied RequirementIds. Do not generate CanonicalRequirementId;
#     the application generates CR-0001, CR-0002 and so on after validation.

# 11. Return strict JSON only. Do not return markdown or code fences.

# IMPORTANT EXAMPLES

# NOT duplicates:
# A. The Supplier must remove a worker who performs poorly.
# B. The Supplier must remove a worker who fails background checks.
# C. The Supplier must remove a worker who fails Clause 7.1 conditions.
# They share a subject and opening structure, but the removal triggers differ.

# Duplicates:
# A. The Supplier must ensure workers perform assignments with due skill, care and
#    diligence.
# B. Perform their Assignment with all due skill, care and diligence.
# The second is a shortened extract of the same obligation.

# REQUIREMENTS

# {requirements_json}

# Return exactly this JSON structure:

# {{
#   "DuplicateGroups": [
#     {{
#       "CanonicalRequirement": "Complete standalone requirement",
#       "RequirementIds": [
#         "REQUIREMENT-ID-1",
#         "REQUIREMENT-ID-2"
#       ],
#       "Reason": "Why these requirements are materially interchangeable"
#     }}
#   ],
#   "UniqueRequirementIds": [
#     "REQUIREMENT-ID-3"
#   ]
# }}
# """.strip()

#     print(
#         "Deduplication prompt prepared:",
#         {
#             "requirementCount": len(llm_requirements),
#             "characterCount": len(prompt),
#             "estimatedTokenCount": round(len(prompt) / 4),
#             "fieldsSentToLlm": [
#                 "RequirementId",
#                 "RequirementText",
#                 "RequirementType",
#             ],
#             "fullOriginalObjectsIncluded": False,
#             "contextIncluded": False,
#             "strictFalseMergeProtection": True,
#         },
#     )

#     return prompt


def build_deduplication_prompt(
    raw_requirements: Any,
    context: Mapping[str, Any] | None = None,
) -> str:
    """
    Build one compact one-go Requirement Deduplication prompt.

    The prompt includes:

    1. Constitution.md
    2. Specification.md
    3. Strict runtime deduplication rules
    4. Compact requirement input

    Only RequirementId, RequirementText and RequirementType are sent
    to the LLM. Original source objects remain in graph state.
    """

    del context

    # ============================================================
    # LOAD CONSTITUTION AND SPECIFICATION
    # ============================================================

    constitution, specification = (
        load_deduplication_instructions()
    )

    # ============================================================
    # NORMALIZE REQUIREMENTS
    # ============================================================

    requirements = normalize_requirements(
        raw_requirements
    )

    if not requirements:
        raise ValueError(
            "Cannot build Requirement Deduplication prompt because "
            "no requirements were supplied."
        )

    # ============================================================
    # BUILD COMPACT LLM INPUT
    # ============================================================

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

        requirement_type = get_requirement_type(
            requirement
        )

        if not requirement_id:
            raise ValueError(
                "A requirement is missing RequirementId at "
                f"position {index}."
            )

        if not requirement_text:
            raise ValueError(
                "A requirement is missing RequirementText at "
                f"position {index}. RequirementId: "
                f"{requirement_id}."
            )

        llm_requirements.append(
            {
                "RequirementId": (
                    requirement_id
                ),
                "RequirementText": (
                    requirement_text
                ),
                "RequirementType": (
                    requirement_type
                ),
            }
        )

    requirements_json = json.dumps(
        llm_requirements,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )

    # ============================================================
    # BUILD FINAL PROMPT
    # ============================================================

    prompt_sections = [
        (
            "REQUIREMENT DEDUPLICATION CONSTITUTION:\n"
            + constitution
        ),
        (
            "REQUIREMENT DEDUPLICATION SPECIFICATION:\n"
            + specification
        ),
        """
RUNTIME TASK

You are a Requirement Deduplication Agent for tender and
procurement requirements.

Evaluate all supplied requirements together in one pass.

Use the Constitution and Specification as mandatory instructions.

Compare requirements using:

- RequirementText as the primary source of meaning.
- RequirementType only as supporting context.
- RequirementId only for traceability.

Do not treat RequirementId as part of the requirement meaning.
""".strip(),
        """
STRICT RUNTIME DECISION STANDARD

Merge requirements only when they express the same complete
material obligation and are interchangeable without changing:

- the supplier's duty;
- required action;
- responsible party;
- trigger;
- scope;
- condition;
- exception;
- legal liability;
- remedy;
- timeframe;
- quantity;
- threshold;
- standard;
- location;
- clause reference;
- evidence requirement;
- service level;
- outcome;
- deliverable.

A false merge is more harmful than a missed duplicate.

When there is uncertainty, keep the requirements separate.
""".strip(),
        """
MANDATORY DEDUPLICATION RULES

1. Similar keywords do not make requirements duplicates.

2. The same topic does not make requirements duplicates.

3. The same customer or supplier does not make requirements
   duplicates.

4. The same RequirementType does not make requirements duplicates.

5. The same opening sentence does not make requirements duplicates.

6. A shared introductory clause followed by different conditions
   represents separate requirements.

7. Keep requirements separate when they differ in any material
   detail, including:

   - action;
   - outcome;
   - trigger;
   - condition;
   - exception;
   - liability;
   - remedy;
   - timeframe;
   - date;
   - quantity;
   - percentage;
   - threshold;
   - location;
   - standard;
   - service level;
   - clause reference;
   - evidence requirement;
   - deliverable;
   - responsible party.

8. Do not merge a general requirement with a specific requirement
   when the specific requirement adds a separate obligation,
   condition, limitation or outcome.

9. RequirementType may help interpretation, but it must not force
   a merge.

10. Different RequirementType values must not prevent otherwise
    identical requirements from being merged.

11. A shortened extract may be a duplicate of a longer requirement
    only when:

    - both express the same complete obligation;
    - the shorter text does not remove a material condition;
    - the shorter text does not change the responsible party;
    - the shorter text does not change the trigger;
    - the shorter text does not add a conflict.

12. Every supplied RequirementId must appear exactly once:

    - either inside one DuplicateGroups item;
    - or inside UniqueRequirementIds.

13. A RequirementId must never appear in multiple groups.

14. Use only RequirementIds supplied in the runtime input.

15. A duplicate group must contain at least two different supplied
    RequirementIds.

16. Do not create a duplicate group containing only one
    RequirementId.

17. Do not generate CanonicalRequirementId.

18. The application generates CanonicalRequirementId values after
    deterministic validation:

    CR-0001
    CR-0002
    CR-0003
    and so on.
""".strip(),
        """
CANONICAL REQUIREMENT RULES

For each DuplicateGroups item, CanonicalRequirement must:

1. Be a complete standalone requirement.

2. Clearly identify the responsible party or subject.

3. Preserve the complete common obligation.

4. Be supported by every grouped source requirement.

5. Contain no material obligation that is absent from any grouped
   source requirement.

6. Not combine different triggers, conditions, remedies, clauses or
   deliverables.

7. Not invent facts, duties, evidence, conditions or commitments.

8. Not start as an incomplete fragment such as:

   - "will, if required...";
   - "are properly briefed...";
   - "perform their Assignment...";
   - "must provide..." when the responsible party is missing.

9. Prefer the most complete original requirement wording when it is
   already a valid standalone statement.

10. Preserve important legal and contractual meaning.
""".strip(),
        """
IMPORTANT NEGATIVE EXAMPLE

The following are NOT duplicates:

A. The Supplier must remove a worker who performs poorly.

B. The Supplier must remove a worker who fails background checks.

C. The Supplier must remove a worker who fails Clause 7.1
   conditions.

These requirements have a similar subject and opening structure,
but each has a materially different removal trigger.

They must remain separate.
""".strip(),
        """
IMPORTANT POSITIVE EXAMPLE

The following may be duplicates:

A. The Supplier must ensure workers perform assignments with due
   skill, care and diligence.

B. Perform their Assignment with all due skill, care and
   diligence.

The second requirement is a shortened extract of the same
obligation, provided the missing surrounding context confirms the
same responsible party and no material condition has been removed.
""".strip(),
        (
            "RUNTIME REQUIREMENTS JSON:\n"
            + requirements_json
        ),
        """
RETURN FORMAT

Return exactly one strict JSON object using this structure:

{
  "DuplicateGroups": [
    {
      "CanonicalRequirement": "Complete standalone requirement",
      "RequirementIds": [
        "REQUIREMENT-ID-1",
        "REQUIREMENT-ID-2"
      ],
      "Reason": "Explain briefly why the requirements express the same complete material obligation."
    }
  ],
  "UniqueRequirementIds": [
    "REQUIREMENT-ID-3"
  ]
}

OUTPUT RULES

1. Return JSON only.

2. Do not return Markdown.

3. Do not return code fences.

4. Do not return explanatory text before or after the JSON.

5. Do not return CanonicalRequirementId.

6. Do not omit any supplied RequirementId.

7. Do not repeat any RequirementId.

8. DuplicateGroups must contain only genuine duplicate groups.

9. UniqueRequirementIds must contain all requirements that are not
   members of a valid duplicate group.
""".strip(),
    ]

    prompt = "\n\n".join(
        section.strip()
        for section in prompt_sections
        if str(section or "").strip()
    )

    # ============================================================
    # LOG SAFE PROMPT METADATA
    # ============================================================

    print(
        "Deduplication prompt prepared:",
        {
            "requirementCount": len(
                llm_requirements
            ),
            "characterCount": len(
                prompt
            ),
            "estimatedTokenCount": round(
                len(prompt) / 4
            ),
            "constitutionCharacters": len(
                constitution
            ),
            "specificationCharacters": len(
                specification
            ),
            "fieldsSentToLlm": [
                "RequirementId",
                "RequirementText",
                "RequirementType",
            ],
            "fullOriginalObjectsIncluded": (
                False
            ),
            "contextIncluded": False,
            "constitutionIncluded": True,
            "specificationIncluded": True,
            "strictFalseMergeProtection": (
                True
            ),
            "standaloneCanonicalRequirementRequired": (
                True
            ),
            "oneGoLlmInvocation": True,
        },
    )

    return prompt

def extract_response_content(llm_response: Any) -> Any:
    """Extract content from LangChain and plain response objects."""

    if llm_response is None:
        raise ValueError("LLM returned no response")

    if isinstance(llm_response, (dict, list)):
        return llm_response

    content = getattr(llm_response, "content", None)

    if content is not None:
        if isinstance(content, list):
            text_parts: list[str] = []

            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, Mapping):
                    text = part.get("text") or part.get("content")

                    if text is not None:
                        text_parts.append(str(text))

            return "\n".join(text_parts)

        return content

    return str(llm_response)


def remove_markdown_code_fence(text: str) -> str:
    """Remove an accidental JSON markdown fence."""

    text = text.strip()
    fenced_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return (
        fenced_match.group(1).strip()
        if fenced_match
        else text
    )


def decode_json_response(text: str) -> Any:
    """Decode JSON even when the model adds surrounding text."""

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
            parsed_value, _ = decoder.raw_decode(text[position:])
            return parsed_value
        except json.JSONDecodeError:
            continue

    raise ValueError(
        "LLM response did not contain valid JSON. "
        f"Response preview: {text[:500]}"
    )


def parse_llm_response(llm_response: Any) -> dict[str, Any]:
    """Convert the LLM response into a Python dictionary."""

    content = extract_response_content(llm_response)

    if isinstance(content, Mapping):
        parsed_result = dict(content)
    elif isinstance(content, list):
        parsed_result = {"DuplicateGroups": content}
    else:
        decoded_value = decode_json_response(str(content))

        if not isinstance(decoded_value, Mapping):
            raise ValueError("LLM JSON response must be an object")

        parsed_result = dict(decoded_value)

    for wrapper_key in (
        "result",
        "Result",
        "output",
        "Output",
        "data",
        "Data",
    ):
        wrapped_result = parsed_result.get(wrapper_key)

        if isinstance(wrapped_result, Mapping):
            parsed_result = dict(wrapped_result)
            break

    return parsed_result


def get_first_value(
    mapping: Mapping[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    """Return the first available property value."""

    for key in keys:
        if key in mapping:
            return mapping[key]

    return default


def normalize_indexes(
    value: Any,
    total_requirements: int,
) -> list[int]:
    """Normalize one-based LLM indexes."""

    if value is None:
        return []

    if not isinstance(value, Sequence) or isinstance(
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

        if 1 <= index <= total_requirements and index not in indexes:
            indexes.append(index)

    return indexes


def normalize_requirement_ids(
    value: Any,
    valid_requirement_ids: set[str],
) -> list[str]:
    """Normalize RequirementIds returned by the LLM."""

    if value is None:
        return []

    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        value = [value]

    normalized_ids: list[str] = []

    for item in value:
        requirement_id = str(item or "").strip()

        if (
            requirement_id
            and requirement_id in valid_requirement_ids
            and requirement_id not in normalized_ids
        ):
            normalized_ids.append(requirement_id)

    return normalized_ids


# ---------------------------------------------------------------------------
# Intent restoration
# ---------------------------------------------------------------------------


def normalize_output_string_list(value: Any) -> list[str]:
    """Return clean, case-insensitively unique strings."""

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

    result: list[str] = []
    seen: set[str] = set()

    for item in values:
        item_text = str(item or "").strip()

        if not item_text:
            continue

        normalized_key = item_text.casefold()

        if normalized_key in seen:
            continue

        seen.add(normalized_key)
        result.append(item_text)

    return result


def collect_requirement_intent_values(
    source_requirements: Sequence[Any],
) -> dict[str, list[str]]:
    """Restore and merge intent fields from original requirements."""

    capability_intents: list[str] = []
    evidence_sections: list[str] = []
    semantic_anchors: list[str] = []

    def collect_from_mapping(
        mapping: Mapping[str, Any],
        depth: int = 0,
    ) -> None:
        if depth > 4:
            return

        capability_intents.extend(
            normalize_output_string_list(
                get_first_value(
                    mapping,
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
                    mapping,
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
                    mapping,
                    "SemanticAnchors",
                    "semantic_anchors",
                    "semanticAnchors",
                    default=[],
                )
            )
        )

        intent_result = get_first_value(
            mapping,
            "IntentResult",
            "intentResult",
            "intent_result",
            default=None,
        )

        if isinstance(intent_result, Mapping):
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

        for nested_key in (
            "Document",
            "document",
            "Requirement",
            "requirement",
            "SourceRequirement",
            "sourceRequirement",
            "Payload",
            "payload",
            "Data",
            "data",
            "Metadata",
            "metadata",
            "Item",
            "item",
        ):
            nested_value = mapping.get(nested_key)

            if isinstance(nested_value, Mapping):
                collect_from_mapping(nested_value, depth + 1)

    for source_requirement in source_requirements:
        if isinstance(source_requirement, Mapping):
            collect_from_mapping(source_requirement)

    return {
        "CapabilityIntent": normalize_output_string_list(
            capability_intents
        ),
        "EvidenceSections": normalize_output_string_list(
            evidence_sections
        ),
        "SemanticAnchors": normalize_output_string_list(
            semantic_anchors
        ),
    }


# ---------------------------------------------------------------------------
# Conservative deterministic duplicate validation
# ---------------------------------------------------------------------------


_COMPARISON_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
}

_NEGATION_WORDS = {
    "no",
    "not",
    "never",
    "neither",
    "nor",
    "without",
    "cannot",
    "cant",
    "wont",
    "mustnt",
    "shallnt",
}

_STANDALONE_PREFIXES = (
    "the supplier ",
    "supplier ",
    "the bidder ",
    "bidder ",
    "the contractor ",
    "contractor ",
    "the provider ",
    "provider ",
    "the authority ",
    "the customer ",
    "cadent ",
    "you ",
    "all suppliers ",
    "each supplier ",
)


def normalize_requirement_for_comparison(value: Any) -> str:
    """Normalize text for deterministic duplicate checks."""

    text = str(value or "").casefold()
    text = (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("won't", "will not")
        .replace("can't", "cannot")
        .replace("mustn't", "must not")
        .replace("shalln't", "shall not")
    )
    text = re.sub(r"[^a-z0-9%£$€\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _comparison_tokens(value: Any) -> list[str]:
    return normalize_requirement_for_comparison(value).split()


def _content_token_set(value: Any) -> set[str]:
    return {
        token
        for token in _comparison_tokens(value)
        if token not in _COMPARISON_STOP_WORDS
    }


def _material_markers(value: Any) -> set[str]:
    """Extract numbers, percentages, money and clause-like markers."""

    normalized = normalize_requirement_for_comparison(value)
    markers = set(
        re.findall(
            r"(?:£|\$|€)?\b\d+(?:\.\d+)?%?\b",
            normalized,
        )
    )

    clause_matches = re.findall(
        r"\b(?:clause|section|schedule|annex|appendix)\s+"
        r"[a-z0-9]+(?:\.[a-z0-9]+)*\b",
        normalized,
    )
    markers.update(clause_matches)
    return markers


def _negation_signature(value: Any) -> set[str]:
    return {
        token
        for token in _comparison_tokens(value)
        if token in _NEGATION_WORDS
    }


def _token_jaccard(first: set[str], second: set[str]) -> float:
    union = first | second
    return len(first & second) / len(union) if union else 0.0


def _token_containment(first: set[str], second: set[str]) -> float:
    smaller_size = min(len(first), len(second))
    return (
        len(first & second) / smaller_size
        if smaller_size
        else 0.0
    )


def _has_material_tail_conflict(
    first_text: str,
    second_text: str,
) -> bool:
    """
    Detect a long shared opening followed by materially different tails.

    This protects against false merges such as multiple worker-removal
    requirements that share the same preamble but have different triggers.
    """

    first_tokens = _comparison_tokens(first_text)
    second_tokens = _comparison_tokens(second_text)

    if not first_tokens or not second_tokens:
        return False

    prefix_length = 0

    for first_token, second_token in zip(
        first_tokens,
        second_tokens,
    ):
        if first_token != second_token:
            break
        prefix_length += 1

    smaller_length = min(
        len(first_tokens),
        len(second_tokens),
    )

    if prefix_length < max(8, int(smaller_length * 0.45)):
        return False

    first_tail = set(first_tokens[prefix_length:])
    second_tail = set(second_tokens[prefix_length:])

    if len(first_tail) < 3 or len(second_tail) < 3:
        return False

    return _token_jaccard(first_tail, second_tail) < 0.35


def are_high_confidence_duplicates(
    first_text: Any,
    second_text: Any,
) -> bool:
    """
    Accept only deterministic, high-confidence duplicate pairs.

    The validator deliberately favours separate requirements over unsafe
    false merges. RequirementType is not used as a hard gate.
    """

    first = normalize_requirement_for_comparison(first_text)
    second = normalize_requirement_for_comparison(second_text)

    if not first or not second:
        return False

    if first == second:
        return True

    if _material_markers(first) != _material_markers(second):
        return False

    if _negation_signature(first) != _negation_signature(second):
        return False

    if _has_material_tail_conflict(first, second):
        return False

    shorter, longer = sorted((first, second), key=len)
    first_tokens = _content_token_set(first)
    second_tokens = _content_token_set(second)

    if not first_tokens or not second_tokens:
        return False

    jaccard = _token_jaccard(first_tokens, second_tokens)
    containment = _token_containment(
        first_tokens,
        second_tokens,
    )
    sequence_similarity = SequenceMatcher(
        None,
        first,
        second,
    ).ratio()

    # Exact shortened extract of the same sufficiently detailed duty.
    if (
        len(shorter) >= 55
        and shorter in longer
        and containment >= 0.92
    ):
        return True

    # Near-identical rewording, punctuation or formatting variation.
    if sequence_similarity >= 0.95 and jaccard >= 0.84:
        return True

    # Strong token containment with close sentence structure.
    if (
        sequence_similarity >= 0.88
        and containment >= 0.94
        and min(len(first), len(second))
        / max(len(first), len(second))
        >= 0.55
    ):
        return True

    return False


def split_unsafe_duplicate_group(
    requirement_indexes: Sequence[int],
    raw_requirements: Sequence[Any],
) -> list[list[int]]:
    """Split an LLM-proposed group using complete-link validation."""

    safe_groups: list[list[int]] = []

    for requirement_index in requirement_indexes:
        zero_based_index = requirement_index - 1

        if not 0 <= zero_based_index < len(raw_requirements):
            continue

        requirement_text = get_requirement_text(
            raw_requirements[zero_based_index]
        )
        placed = False

        for safe_group in safe_groups:
            if all(
                are_high_confidence_duplicates(
                    requirement_text,
                    get_requirement_text(
                        raw_requirements[existing_index - 1]
                    ),
                )
                for existing_index in safe_group
            ):
                safe_group.append(requirement_index)
                placed = True
                break

        if not placed:
            safe_groups.append([requirement_index])

    return safe_groups


def _clusters_are_compatible(
    first_cluster: Sequence[int],
    second_cluster: Sequence[int],
    requirements: Sequence[Any],
) -> bool:
    """Require every cross-cluster pair to be a safe duplicate."""

    return all(
        are_high_confidence_duplicates(
            get_requirement_text(requirements[first_index - 1]),
            get_requirement_text(requirements[second_index - 1]),
        )
        for first_index in first_cluster
        for second_index in second_cluster
    )


def merge_safe_final_clusters(
    clusters: Sequence[Sequence[int]],
    requirements: Sequence[Any],
) -> list[list[int]]:
    """Merge high-confidence duplicates the LLM left separate."""

    merged_clusters: list[list[int]] = []

    for raw_cluster in sorted(
        (list(cluster) for cluster in clusters if cluster),
        key=lambda cluster: min(cluster),
    ):
        cluster = sorted(set(raw_cluster))
        matching_cluster: list[int] | None = None

        for existing_cluster in merged_clusters:
            if _clusters_are_compatible(
                existing_cluster,
                cluster,
                requirements,
            ):
                matching_cluster = existing_cluster
                break

        if matching_cluster is None:
            merged_clusters.append(cluster)
        else:
            matching_cluster.extend(cluster)
            matching_cluster[:] = sorted(set(matching_cluster))

    return sorted(merged_clusters, key=lambda cluster: min(cluster))


def _is_standalone_requirement(text: str) -> bool:
    normalized = normalize_requirement_for_comparison(text)
    return normalized.startswith(_STANDALONE_PREFIXES)


def select_canonical_requirement(
    requirement_indexes: Sequence[int],
    requirements: Sequence[Any],
) -> tuple[str, int]:
    """
    Select the safest canonical text from original source requirements.

    No new obligation is generated. A complete standalone source sentence is
    preferred over a shorter fragment.
    """

    candidates: list[tuple[int, str]] = [
        (
            requirement_index,
            get_requirement_text(
                requirements[requirement_index - 1]
            ).strip(),
        )
        for requirement_index in requirement_indexes
    ]

    if not candidates:
        return "", 0

    def score(candidate: tuple[int, str]) -> tuple[int, int, int]:
        _, text = candidate
        standalone_bonus = 1 if _is_standalone_requirement(text) else 0
        punctuation_bonus = 1 if text.endswith((".", ";", ":")) else 0
        return (
            standalone_bonus,
            punctuation_bonus,
            len(text),
        )

    selected_index, selected_text = max(candidates, key=score)
    return selected_text, selected_index


# ---------------------------------------------------------------------------
# Final result validation and construction
# ---------------------------------------------------------------------------


def validate_deduplication_result(
    result: Any,
    raw_requirements: Any,
) -> dict[str, Any]:
    """
    Validate the one-go LLM response and build safe final output.

    Safety behaviour:
    - every input requirement is represented exactly once;
    - unsafe LLM groups are split deterministically;
    - high-confidence duplicates missed by the LLM are merged;
    - IDs are assigned continuously as CR-0001, CR-0002, ...;
    - summary values are calculated in Python, never trusted from the LLM.
    """

    requirements = normalize_requirements(raw_requirements)

    if not requirements:
        raise ValueError(
            "No raw requirements are available for validation"
        )

    if not isinstance(result, Mapping):
        raise ValueError(
            "Deduplication result must be a dictionary"
        )

    total_requirements = len(requirements)
    requirement_id_to_index: dict[str, int] = {}
    requirement_index_to_id: dict[int, str] = {}

    for index, requirement in enumerate(requirements, start=1):
        requirement_id = get_requirement_id(requirement, index)

        if requirement_id in requirement_id_to_index:
            raise ValueError(
                "Duplicate RequirementId found in input: "
                f"{requirement_id}"
            )

        requirement_id_to_index[requirement_id] = index
        requirement_index_to_id[index] = requirement_id

    valid_requirement_ids = set(requirement_id_to_index)
    raw_duplicate_groups = get_first_value(
        result,
        "DuplicateGroups",
        "duplicate_groups",
        "Groups",
        "groups",
        default=[],
    )

    if not isinstance(raw_duplicate_groups, Sequence) or isinstance(
        raw_duplicate_groups,
        (str, bytes, bytearray),
    ):
        raw_duplicate_groups = []

    accepted_clusters: list[list[int]] = []
    assigned_indexes: set[int] = set()
    rejected_false_merge_members = 0
    proposed_group_count = 0

    for raw_group in raw_duplicate_groups:
        if not isinstance(raw_group, Mapping):
            continue

        requirement_ids = normalize_requirement_ids(
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

        requirement_indexes = [
            requirement_id_to_index[requirement_id]
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

        requirement_indexes = [
            index
            for index in requirement_indexes
            if index not in assigned_indexes
        ]

        if len(requirement_indexes) < 2:
            continue

        proposed_group_count += 1
        safe_groups = split_unsafe_duplicate_group(
            requirement_indexes,
            requirements,
        )

        for safe_group in safe_groups:
            if len(safe_group) >= 2:
                accepted_clusters.append(safe_group)
                assigned_indexes.update(safe_group)
            else:
                rejected_false_merge_members += 1

    # LLM unique IDs are accepted for coverage, but every unassigned input is
    # included automatically, so malformed/missing unique arrays cannot lose data.
    requested_unique_ids = normalize_requirement_ids(
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

    requested_unique_indexes = [
        requirement_id_to_index[requirement_id]
        for requirement_id in requested_unique_ids
    ]

    if not requested_unique_indexes:
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

    singleton_indexes: list[int] = []

    for index in requested_unique_indexes:
        if index not in assigned_indexes and index not in singleton_indexes:
            singleton_indexes.append(index)

    for index in range(1, total_requirements + 1):
        if index not in assigned_indexes and index not in singleton_indexes:
            singleton_indexes.append(index)

    provisional_clusters: list[list[int]] = [
        sorted(set(cluster))
        for cluster in accepted_clusters
    ] + [[index] for index in singleton_indexes]

    final_clusters = merge_safe_final_clusters(
        provisional_clusters,
        requirements,
    )

    represented_indexes = [
        index
        for cluster in final_clusters
        for index in cluster
    ]

    if sorted(represented_indexes) != list(
        range(1, total_requirements + 1)
    ):
        raise ValueError(
            "Internal deduplication validation failed: every input "
            "requirement must appear exactly once."
        )

    deduplicated_requirements: list[dict[str, Any]] = []

    for canonical_number, cluster in enumerate(
        final_clusters,
        start=1,
    ):
        source_requirements = [
            requirements[index - 1]
            for index in cluster
        ]
        canonical_requirement, canonical_source_index = (
            select_canonical_requirement(
                cluster,
                requirements,
            )
        )
        intent_values = collect_requirement_intent_values(
            source_requirements
        )
        canonical_source_requirement = (
            requirements[canonical_source_index - 1]
            if canonical_source_index
            else source_requirements[0]
        )

        deduplicated_requirements.append(
            {
                "CanonicalRequirementId": (
                    f"CR-{canonical_number:04d}"
                ),
                "CanonicalRequirement": canonical_requirement,
                "RequirementIds": [
                    requirement_index_to_id[index]
                    for index in cluster
                ],
                "RequirementType": get_requirement_type(
                    canonical_source_requirement
                ),
                "IntentResult": {
                    "CapabilityIntent": intent_values[
                        "CapabilityIntent"
                    ],
                    "EvidenceSections": intent_values[
                        "EvidenceSections"
                    ],
                    "SemanticAnchors": intent_values[
                        "SemanticAnchors"
                    ],
                },
            }
        )

    total_deduplicated_requirements = len(
        deduplicated_requirements
    )
    duplicates_removed = max(
        0,
        total_requirements - total_deduplicated_requirements,
    )

    print(
        "Deterministic deduplication validation completed:",
        {
            "inputRequirementCount": total_requirements,
            "llmProposedDuplicateGroupCount": proposed_group_count,
            "unsafeGroupMembersReturnedToUniquePool": (
                rejected_false_merge_members
            ),
            "acceptedOutputCount": total_deduplicated_requirements,
            "duplicatesRemoved": duplicates_removed,
            "canonicalIdStart": (
                "CR-0001"
                if deduplicated_requirements
                else None
            ),
            "canonicalIdEnd": (
                deduplicated_requirements[-1][
                    "CanonicalRequirementId"
                ]
                if deduplicated_requirements
                else None
            ),
        },
    )

    return {
        "Summary": {
            "TotalInputRequirements": total_requirements,
            "TotalDeduplicatedRequirements": (
                total_deduplicated_requirements
            ),
            "DuplicatesRemoved": duplicates_removed,
        },
        "DeduplicatedRequirements": deduplicated_requirements,
    }


def extract_deduplication_result(
    final_state: Mapping[str, Any] | Any,
) -> dict[str, Any]:
    """Extract the final validated result from LangGraph."""

    if not isinstance(final_state, Mapping):
        raise ValueError(
            "LangGraph returned an invalid final state"
        )

    error = final_state.get("error")

    if error:
        raise RuntimeError(str(error))

    result = final_state.get("result")

    if not isinstance(result, Mapping):
        raise ValueError(
            "LangGraph completed without a valid deduplication result"
        )

    return dict(result)