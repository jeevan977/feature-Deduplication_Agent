

# from __future__ import annotations

# import asyncio
# import os
# import re
# import unicodedata
# from collections import Counter, defaultdict
# from difflib import SequenceMatcher
# from typing import Any, Mapping, Optional, Sequence

# from langchain_core.runnables import RunnableConfig

# from app.infrastructure.load_llms import create_llm
# from app.infrastructure.logger import Logging

# from app.agents.Deduplication_Agent.graph.workflow import (
#     build_deduplication_graph,
# )
# from app.utils.helpers import (
#     build_initial_state,
#     collect_requirement_intent_values,
#     extract_deduplication_result,
#     get_requirement_id,
#     get_requirement_text,
#     get_requirement_type,
#     normalize_output_string_list,
#     normalize_requirements,
# )


# _STOP_WORDS = {
#     "a",
#     "an",
#     "and",
#     "any",
#     "are",
#     "as",
#     "at",
#     "be",
#     "bidding",
#     "by",
#     "confirm",
#     "entity",
#     "for",
#     "from",
#     "in",
#     "include",
#     "included",
#     "includes",
#     "including",
#     "is",
#     "it",
#     "its",
#     "must",
#     "of",
#     "on",
#     "or",
#     "organisation",
#     "organization",
#     "our",
#     "please",
#     "shall",
#     "should",
#     "supplier",
#     "suppliers",
#     "that",
#     "the",
#     "their",
#     "these",
#     "this",
#     "those",
#     "to",
#     "under",
#     "we",
#     "will",
#     "with",
#     "within",
#     "you",
#     "your",
# }


# def _normalize_comparison_text(
#     value: Any,
# ) -> str:
#     text = unicodedata.normalize(
#         "NFKC",
#         str(value or ""),
#     ).lower()

#     text = (
#         text.replace("’", "'")
#         .replace("“", '"')
#         .replace("”", '"')
#         .replace("–", "-")
#         .replace("—", "-")
#     )

#     text = re.sub(
#         r"[^a-z0-9£%]+",
#         " ",
#         text,
#     )

#     return re.sub(
#         r"\s+",
#         " ",
#         text,
#     ).strip()


# def _comparison_tokens(
#     text: str,
# ) -> set[str]:
#     return {
#         token
#         for token in _normalize_comparison_text(
#             text
#         ).split()
#         if len(token) > 2
#         and token not in _STOP_WORDS
#     }


# def _normalized_requirement_type(
#     requirement: Any,
# ) -> str:
#     return _normalize_comparison_text(
#         get_requirement_type(
#             requirement
#         )
#     )


# def _semantic_anchor_tokens(
#     requirement: Any,
# ) -> set[str]:
#     intent_values = (
#         collect_requirement_intent_values(
#             [requirement]
#         )
#     )

#     anchors = intent_values.get(
#         "SemanticAnchors",
#         [],
#     )

#     return {
#         _normalize_comparison_text(anchor)
#         for anchor in anchors
#         if _normalize_comparison_text(anchor)
#     }


# def _is_candidate_pair(
#     left: Any,
#     right: Any,
# ) -> bool:
#     """
#     Broadly identify requirements that may be duplicates.

#     This is only candidate generation. Except for exact normalized
#     text, the LLM makes the final duplicate decision.
#     """

#     left_text = _normalize_comparison_text(
#         get_requirement_text(left)
#     )

#     right_text = _normalize_comparison_text(
#         get_requirement_text(right)
#     )

#     if not left_text or not right_text:
#         return False

#     if left_text == right_text:
#         return True

#     left_tokens = _comparison_tokens(
#         left_text
#     )

#     right_tokens = _comparison_tokens(
#         right_text
#     )

#     token_intersection = len(
#         left_tokens
#         & right_tokens
#     )

#     token_union = len(
#         left_tokens
#         | right_tokens
#     )

#     token_jaccard = (
#         token_intersection
#         / token_union
#         if token_union
#         else 0.0
#     )

#     minimum_token_count = min(
#         len(left_tokens),
#         len(right_tokens),
#     )

#     token_containment = (
#         token_intersection
#         / minimum_token_count
#         if minimum_token_count
#         else 0.0
#     )

#     sequence_ratio = SequenceMatcher(
#         None,
#         left_text,
#         right_text,
#     ).ratio()

#     length_ratio = (
#         min(
#             len(left_text),
#             len(right_text),
#         )
#         / max(
#             len(left_text),
#             len(right_text),
#         )
#     )

#     left_anchors = _semantic_anchor_tokens(
#         left
#     )

#     right_anchors = _semantic_anchor_tokens(
#         right
#     )

#     anchor_intersection = len(
#         left_anchors
#         & right_anchors
#     )

#     minimum_anchor_count = min(
#         len(left_anchors),
#         len(right_anchors),
#     )

#     anchor_containment = (
#         anchor_intersection
#         / minimum_anchor_count
#         if minimum_anchor_count
#         else 0.0
#     )

#     left_type = _normalized_requirement_type(
#         left
#     )

#     right_type = _normalized_requirement_type(
#         right
#     )

#     same_type = bool(
#         left_type
#         and left_type == right_type
#     )

#     return bool(
#         sequence_ratio >= 0.93
#         or token_jaccard >= 0.90
#         or (
#             sequence_ratio >= 0.84
#             and token_jaccard >= 0.72
#             and length_ratio >= 0.65
#         )
#         or (
#             token_containment >= 0.90
#             and length_ratio >= 0.70
#             and sequence_ratio >= 0.78
#         )
#         or (
#             anchor_containment >= 0.75
#             and sequence_ratio >= 0.76
#             and (
#                 same_type
#                 or token_jaccard >= 0.65
#             )
#         )
#     )


# def _build_candidate_components(
#     requirements: Sequence[Any],
# ) -> list[list[int]]:
#     """
#     Compare every requirement globally before any LLM batching.

#     Requirements connected by exact or near-duplicate evidence are
#     placed into the same candidate component. This prevents loss of
#     duplicates across arbitrary batches.
#     """

#     requirement_count = len(
#         requirements
#     )

#     parents = list(
#         range(requirement_count)
#     )

#     ranks = [0] * requirement_count

#     def find(index: int) -> int:
#         while parents[index] != index:
#             parents[index] = parents[
#                 parents[index]
#             ]
#             index = parents[index]

#         return index

#     def union(
#         left_index: int,
#         right_index: int,
#     ) -> None:
#         left_root = find(
#             left_index
#         )

#         right_root = find(
#             right_index
#         )

#         if left_root == right_root:
#             return

#         if ranks[left_root] < ranks[
#             right_root
#         ]:
#             parents[left_root] = (
#                 right_root
#             )

#         elif ranks[left_root] > ranks[
#             right_root
#         ]:
#             parents[right_root] = (
#                 left_root
#             )

#         else:
#             parents[right_root] = (
#                 left_root
#             )
#             ranks[left_root] += 1

#     for left_index in range(
#         requirement_count
#     ):
#         for right_index in range(
#             left_index + 1,
#             requirement_count,
#         ):
#             if _is_candidate_pair(
#                 requirements[left_index],
#                 requirements[right_index],
#             ):
#                 union(
#                     left_index,
#                     right_index,
#                 )

#     components_by_root: dict[
#         int,
#         list[int],
#     ] = defaultdict(list)

#     for index in range(
#         requirement_count
#     ):
#         components_by_root[
#             find(index)
#         ].append(index)

#     return sorted(
#         components_by_root.values(),
#         key=lambda component: component[0],
#     )


# def _all_same_normalized_text(
#     requirements: Sequence[Any],
# ) -> bool:
#     normalized_texts = {
#         _normalize_comparison_text(
#             get_requirement_text(
#                 requirement
#             )
#         )
#         for requirement in requirements
#     }

#     normalized_texts.discard("")

#     return len(normalized_texts) <= 1


# def _merge_requirement_ids(
#     requirements: Sequence[Any],
#     index_lookup: Mapping[int, int],
# ) -> list[str]:
#     requirement_ids: list[str] = []
#     seen_ids: set[str] = set()

#     for requirement in requirements:
#         requirement_index = (
#             index_lookup.get(
#                 id(requirement),
#                 len(requirement_ids) + 1,
#             )
#         )

#         requirement_id = get_requirement_id(
#             requirement,
#             requirement_index,
#         )

#         if requirement_id in seen_ids:
#             continue

#         seen_ids.add(
#             requirement_id
#         )
#         requirement_ids.append(
#             requirement_id
#         )

#     return requirement_ids


# def _select_requirement_type(
#     requirements: Sequence[Any],
# ) -> str:
#     requirement_types = [
#         get_requirement_type(
#             requirement
#         ).strip()
#         for requirement in requirements
#         if get_requirement_type(
#             requirement
#         ).strip()
#     ]

#     if not requirement_types:
#         return ""

#     counts = Counter(
#         requirement_types
#     )

#     return counts.most_common(1)[0][0]


# def _build_compact_item(
#     requirements: Sequence[Any],
#     *,
#     canonical_requirement: str | None,
#     index_lookup: Mapping[int, int],
# ) -> dict[str, Any]:
#     source_requirements = list(
#         requirements
#     )

#     if not source_requirements:
#         raise ValueError(
#             "Cannot build a deduplicated item "
#             "without source requirements."
#         )

#     canonical_text = str(
#         canonical_requirement
#         or get_requirement_text(
#             source_requirements[0]
#         )
#         or ""
#     ).strip()

#     intent_result = (
#         collect_requirement_intent_values(
#             source_requirements
#         )
#     )

#     return {
#         "CanonicalRequirement": (
#             canonical_text
#         ),
#         "RequirementIds": (
#             _merge_requirement_ids(
#                 source_requirements,
#                 index_lookup,
#             )
#         ),
#         "RequirementType": (
#             _select_requirement_type(
#                 source_requirements
#             )
#         ),
#         "IntentResult": {
#             "CapabilityIntent": (
#                 normalize_output_string_list(
#                     intent_result.get(
#                         "CapabilityIntent",
#                         [],
#                     )
#                 )
#             ),
#             "EvidenceSections": (
#                 normalize_output_string_list(
#                     intent_result.get(
#                         "EvidenceSections",
#                         [],
#                     )
#                 )
#             ),
#             "SemanticAnchors": (
#                 normalize_output_string_list(
#                     intent_result.get(
#                         "SemanticAnchors",
#                         [],
#                     )
#                 )
#             ),
#         },
#     }


# def _fallback_exact_and_unique_items(
#     requirements: Sequence[Any],
#     *,
#     index_lookup: Mapping[int, int],
# ) -> list[dict[str, Any]]:
#     """
#     Safe fallback used only if an LLM candidate-group call fails.

#     Exact normalized duplicates remain merged. Materially uncertain
#     requirements remain unique rather than being incorrectly merged.
#     """

#     grouped_requirements: dict[
#         str,
#         list[Any],
#     ] = defaultdict(list)

#     ordered_keys: list[str] = []

#     for requirement in requirements:
#         normalized_text = (
#             _normalize_comparison_text(
#                 get_requirement_text(
#                     requirement
#                 )
#             )
#         )

#         group_key = (
#             normalized_text
#             or f"__EMPTY__{id(requirement)}"
#         )

#         if group_key not in (
#             grouped_requirements
#         ):
#             ordered_keys.append(
#                 group_key
#             )

#         grouped_requirements[
#             group_key
#         ].append(requirement)

#     return [
#         _build_compact_item(
#             grouped_requirements[group_key],
#             canonical_requirement=(
#                 get_requirement_text(
#                     grouped_requirements[
#                         group_key
#                     ][0]
#                 )
#             ),
#             index_lookup=index_lookup,
#         )
#         for group_key in ordered_keys
#     ]


# def _enrich_llm_items(
#     result: Mapping[str, Any],
#     component_requirements: Sequence[Any],
#     *,
#     index_lookup: Mapping[int, int],
# ) -> list[dict[str, Any]]:
#     raw_items = result.get(
#         "DeduplicatedRequirements",
#         [],
#     )

#     if not isinstance(
#         raw_items,
#         Sequence,
#     ) or isinstance(
#         raw_items,
#         (str, bytes, bytearray),
#     ):
#         raise ValueError(
#             "The LLM candidate-group result does not "
#             "contain DeduplicatedRequirements."
#         )

#     source_by_id: dict[
#         str,
#         Any,
#     ] = {}

#     expected_ids: list[str] = []

#     for requirement in component_requirements:
#         requirement_index = index_lookup.get(
#             id(requirement),
#             len(expected_ids) + 1,
#         )

#         requirement_id = get_requirement_id(
#             requirement,
#             requirement_index,
#         )

#         source_by_id[
#             requirement_id
#         ] = requirement

#         expected_ids.append(
#             requirement_id
#         )

#     enriched_items: list[
#         dict[str, Any]
#     ] = []

#     represented_ids: list[str] = []

#     for raw_item in raw_items:
#         if not isinstance(
#             raw_item,
#             Mapping,
#         ):
#             continue

#         raw_requirement_ids = (
#             raw_item.get(
#                 "RequirementIds",
#                 [],
#             )
#         )

#         if not isinstance(
#             raw_requirement_ids,
#             Sequence,
#         ) or isinstance(
#             raw_requirement_ids,
#             (str, bytes, bytearray),
#         ):
#             raw_requirement_ids = [
#                 raw_requirement_ids
#             ]

#         requirement_ids: list[str] = []
#         source_requirements: list[Any] = []

#         for raw_requirement_id in (
#             raw_requirement_ids
#         ):
#             requirement_id = str(
#                 raw_requirement_id
#             ).strip()

#             if (
#                 not requirement_id
#                 or requirement_id
#                 not in source_by_id
#                 or requirement_id
#                 in requirement_ids
#             ):
#                 continue

#             requirement_ids.append(
#                 requirement_id
#             )

#             source_requirements.append(
#                 source_by_id[
#                     requirement_id
#                 ]
#             )

#         if not source_requirements:
#             continue

#         represented_ids.extend(
#             requirement_ids
#         )

#         enriched_items.append(
#             _build_compact_item(
#                 source_requirements,
#                 canonical_requirement=str(
#                     raw_item.get(
#                         "CanonicalRequirement",
#                         "",
#                     )
#                     or ""
#                 ).strip(),
#                 index_lookup=index_lookup,
#             )
#         )

#     if Counter(represented_ids) != Counter(
#         expected_ids
#     ):
#         missing_ids = list(
#             (
#                 Counter(expected_ids)
#                 - Counter(represented_ids)
#             ).elements()
#         )

#         repeated_ids = list(
#             (
#                 Counter(represented_ids)
#                 - Counter(expected_ids)
#             ).elements()
#         )

#         raise ValueError(
#             "The LLM candidate-group result did not "
#             "represent every requirement exactly once. "
#             f"Missing IDs: {missing_ids[:20]}. "
#             f"Unexpected/repeated IDs: "
#             f"{repeated_ids[:20]}."
#         )

#     return enriched_items


# def _consolidate_exact_output_items(
#     items: Sequence[Mapping[str, Any]],
#     source_by_id: Mapping[str, Any],
#     *,
#     index_lookup: Mapping[int, int],
# ) -> list[dict[str, Any]]:
#     """
#     Perform a final global exact-text consolidation after all candidate
#     components have been processed.
#     """

#     grouped_items: dict[
#         str,
#         list[Mapping[str, Any]],
#     ] = defaultdict(list)

#     ordered_keys: list[str] = []

#     for item_index, item in enumerate(
#         items,
#         start=1,
#     ):
#         normalized_text = (
#             _normalize_comparison_text(
#                 item.get(
#                     "CanonicalRequirement",
#                     "",
#                 )
#             )
#         )

#         group_key = (
#             normalized_text
#             or f"__OUTPUT__{item_index}"
#         )

#         if group_key not in grouped_items:
#             ordered_keys.append(
#                 group_key
#             )

#         grouped_items[
#             group_key
#         ].append(item)

#     consolidated_items: list[
#         dict[str, Any]
#     ] = []

#     for group_key in ordered_keys:
#         grouped = grouped_items[
#             group_key
#         ]

#         requirement_ids: list[str] = []
#         source_requirements: list[Any] = []

#         for item in grouped:
#             for raw_requirement_id in item.get(
#                 "RequirementIds",
#                 [],
#             ):
#                 requirement_id = str(
#                     raw_requirement_id
#                 ).strip()

#                 if (
#                     not requirement_id
#                     or requirement_id
#                     in requirement_ids
#                 ):
#                     continue

#                 requirement_ids.append(
#                     requirement_id
#                 )

#                 source_requirement = (
#                     source_by_id.get(
#                         requirement_id
#                     )
#                 )

#                 if source_requirement is not None:
#                     source_requirements.append(
#                         source_requirement
#                     )

#         if source_requirements:
#             consolidated_items.append(
#                 _build_compact_item(
#                     source_requirements,
#                     canonical_requirement=str(
#                         grouped[0].get(
#                             "CanonicalRequirement",
#                             "",
#                         )
#                         or ""
#                     ).strip(),
#                     index_lookup=index_lookup,
#                 )
#             )

#         else:
#             consolidated_items.append(
#                 {
#                     "CanonicalRequirement": str(
#                         grouped[0].get(
#                             "CanonicalRequirement",
#                             "",
#                         )
#                         or ""
#                     ).strip(),
#                     "RequirementIds": (
#                         requirement_ids
#                     ),
#                     "RequirementType": str(
#                         grouped[0].get(
#                             "RequirementType",
#                             "",
#                         )
#                         or ""
#                     ).strip(),
#                     "IntentResult": dict(
#                         grouped[0].get(
#                             "IntentResult",
#                             {},
#                         )
#                         or {}
#                     ),
#                 }
#             )

#     return consolidated_items


# def _repair_global_coverage(
#     items: Sequence[Mapping[str, Any]],
#     requirements: Sequence[Any],
#     *,
#     index_lookup: Mapping[int, int],
# ) -> list[dict[str, Any]]:
#     """
#     Ensure every original RequirementId appears exactly once in the
#     final compact result.
#     """

#     source_by_id: dict[
#         str,
#         Any,
#     ] = {}

#     ordered_expected_ids: list[str] = []

#     for requirement in requirements:
#         requirement_index = index_lookup.get(
#             id(requirement),
#             len(ordered_expected_ids) + 1,
#         )

#         requirement_id = get_requirement_id(
#             requirement,
#             requirement_index,
#         )

#         source_by_id[
#             requirement_id
#         ] = requirement

#         ordered_expected_ids.append(
#             requirement_id
#         )

#     used_ids: set[str] = set()
#     repaired_items: list[
#         dict[str, Any]
#     ] = []

#     for item in items:
#         retained_ids: list[str] = []

#         for raw_requirement_id in item.get(
#             "RequirementIds",
#             [],
#         ):
#             requirement_id = str(
#                 raw_requirement_id
#             ).strip()

#             if (
#                 not requirement_id
#                 or requirement_id
#                 not in source_by_id
#                 or requirement_id
#                 in used_ids
#             ):
#                 continue

#             used_ids.add(
#                 requirement_id
#             )

#             retained_ids.append(
#                 requirement_id
#             )

#         if not retained_ids:
#             continue

#         source_requirements = [
#             source_by_id[
#                 requirement_id
#             ]
#             for requirement_id in retained_ids
#         ]

#         repaired_items.append(
#             _build_compact_item(
#                 source_requirements,
#                 canonical_requirement=str(
#                     item.get(
#                         "CanonicalRequirement",
#                         "",
#                     )
#                     or ""
#                 ).strip(),
#                 index_lookup=index_lookup,
#             )
#         )

#     for requirement_id in (
#         ordered_expected_ids
#     ):
#         if requirement_id in used_ids:
#             continue

#         source_requirement = source_by_id[
#             requirement_id
#         ]

#         repaired_items.append(
#             _build_compact_item(
#                 [source_requirement],
#                 canonical_requirement=(
#                     get_requirement_text(
#                         source_requirement
#                     )
#                 ),
#                 index_lookup=index_lookup,
#             )
#         )

#         used_ids.add(
#             requirement_id
#         )

#     return repaired_items


# def _assign_final_ids(
#     items: Sequence[Mapping[str, Any]],
# ) -> list[dict[str, Any]]:
#     duplicate_number = 1
#     unique_number = 1

#     final_items: list[
#         dict[str, Any]
#     ] = []

#     # Keep duplicate groups first for easier MongoDB inspection.
#     ordered_items = sorted(
#         items,
#         key=lambda item: (
#             0
#             if len(
#                 item.get(
#                     "RequirementIds",
#                     [],
#                 )
#             ) > 1
#             else 1
#         ),
#     )

#     for item in ordered_items:
#         requirement_ids = list(
#             item.get(
#                 "RequirementIds",
#                 [],
#             )
#         )

#         if len(requirement_ids) > 1:
#             deduplicated_requirement_id = (
#                 f"DEDUP-GROUP-"
#                 f"{duplicate_number:04d}"
#             )

#             duplicate_number += 1

#         else:
#             deduplicated_requirement_id = (
#                 f"DEDUP-UNIQUE-"
#                 f"{unique_number:04d}"
#             )

#             unique_number += 1

#         final_items.append(
#             {
#                 "DeduplicatedRequirementId": (
#                     deduplicated_requirement_id
#                 ),
#                 "CanonicalRequirement": str(
#                     item.get(
#                         "CanonicalRequirement",
#                         "",
#                     )
#                     or ""
#                 ).strip(),
#                 "RequirementIds": (
#                     requirement_ids
#                 ),
#                 "RequirementType": str(
#                     item.get(
#                         "RequirementType",
#                         "",
#                     )
#                     or ""
#                 ).strip(),
#                 "IntentResult": {
#                     "CapabilityIntent": (
#                         normalize_output_string_list(
#                             (
#                                 item.get(
#                                     "IntentResult",
#                                     {},
#                                 )
#                                 or {}
#                             ).get(
#                                 "CapabilityIntent",
#                                 [],
#                             )
#                         )
#                     ),
#                     "EvidenceSections": (
#                         normalize_output_string_list(
#                             (
#                                 item.get(
#                                     "IntentResult",
#                                     {},
#                                 )
#                                 or {}
#                             ).get(
#                                 "EvidenceSections",
#                                 [],
#                             )
#                         )
#                     ),
#                     "SemanticAnchors": (
#                         normalize_output_string_list(
#                             (
#                                 item.get(
#                                     "IntentResult",
#                                     {},
#                                 )
#                                 or {}
#                             ).get(
#                                 "SemanticAnchors",
#                                 [],
#                             )
#                         )
#                     ),
#                 },
#             }
#         )

#     return final_items


# class RequirementDeduplicationAgent:
#     def __init__(
#         self,
#         llm: Any | None = None,
#         graph: Any | None = None,
#     ) -> None:
#         self._llm = llm
#         self._graph = graph

#         self._logger = Logging(
#             agent_name=(
#                 "Requirement Deduplication Agent"
#             ),
#             source_module=(
#                 "app.agents."
#                 "Deduplication_Agent.Agent"
#             ),
#         )

#     @property
#     def llm(self) -> Any:
#         if self._llm is None:
#             self._llm = create_llm()

#         return self._llm

#     @property
#     def graph(self) -> Any:
#         if self._graph is None:
#             self._graph = (
#                 build_deduplication_graph(
#                     llm=self.llm,
#                 )
#             )

#         return self._graph

#     @property
#     def max_llm_group_size(self) -> int:
#         return max(
#             5,
#             int(
#                 os.getenv(
#                     "DEDUPLICATION_MAX_LLM_GROUP_SIZE",
#                     "40",
#                 )
#             ),
#         )

#     def _partition_large_component(
#         self,
#         component_requirements: Sequence[Any],
#     ) -> list[list[Any]]:
#         """
#         Large candidate components are uncommon. Partition by
#         RequirementType before using fixed-size chunks so one huge
#         prompt can never recreate the original context-limit problem.
#         """

#         if (
#             len(component_requirements)
#             <= self.max_llm_group_size
#         ):
#             return [
#                 list(component_requirements)
#             ]

#         requirements_by_type: dict[
#             str,
#             list[Any],
#         ] = defaultdict(list)

#         type_order: list[str] = []

#         for requirement in (
#             component_requirements
#         ):
#             requirement_type = (
#                 _normalized_requirement_type(
#                     requirement
#                 )
#                 or "__UNSPECIFIED__"
#             )

#             if (
#                 requirement_type
#                 not in requirements_by_type
#             ):
#                 type_order.append(
#                     requirement_type
#                 )

#             requirements_by_type[
#                 requirement_type
#             ].append(requirement)

#         partitions: list[list[Any]] = []

#         for requirement_type in type_order:
#             typed_requirements = (
#                 requirements_by_type[
#                     requirement_type
#                 ]
#             )

#             for start_index in range(
#                 0,
#                 len(typed_requirements),
#                 self.max_llm_group_size,
#             ):
#                 partitions.append(
#                     typed_requirements[
#                         start_index:
#                         start_index
#                         + self.max_llm_group_size
#                     ]
#                 )

#         return partitions

#     async def _process_candidate_partition(
#         self,
#         partition_requirements: Sequence[Any],
#         *,
#         context_data: Mapping[str, Any],
#         bearer_token: str | None,
#         correlation_id: str,
#         config: RunnableConfig | None,
#         index_lookup: Mapping[int, int],
#     ) -> tuple[list[dict[str, Any]], bool]:
#         if len(partition_requirements) == 1:
#             return (
#                 _fallback_exact_and_unique_items(
#                     partition_requirements,
#                     index_lookup=index_lookup,
#                 ),
#                 False,
#             )

#         if _all_same_normalized_text(
#             partition_requirements
#         ):
#             return (
#                 [
#                     _build_compact_item(
#                         partition_requirements,
#                         canonical_requirement=(
#                             get_requirement_text(
#                                 partition_requirements[
#                                     0
#                                 ]
#                             )
#                         ),
#                         index_lookup=index_lookup,
#                     )
#                 ],
#                 False,
#             )

#         try:
#             initial_state = build_initial_state(
#                 raw_requirements=list(
#                     partition_requirements
#                 ),
#                 context=context_data,
#                 bearer_token=bearer_token,
#                 correlation_id=correlation_id,
#             )

#             final_state = await self.graph.ainvoke(
#                 initial_state,
#                 config=config,
#             )

#             result = (
#                 extract_deduplication_result(
#                     final_state
#                 )
#             )

#             return (
#                 _enrich_llm_items(
#                     result,
#                     partition_requirements,
#                     index_lookup=index_lookup,
#                 ),
#                 True,
#             )

#         except Exception as exc:
#             print(
#                 "Candidate-group LLM verification "
#                 "failed. Exact duplicate fallback "
#                 "will be used:",
#                 {
#                     "requirementCount": len(
#                         partition_requirements
#                     ),
#                     "errorType": (
#                         type(exc).__name__
#                     ),
#                     "message": str(exc),
#                 },
#             )

#             return (
#                 _fallback_exact_and_unique_items(
#                     partition_requirements,
#                     index_lookup=index_lookup,
#                 ),
#                 True,
#             )

#     async def deduplicate(
#         self,
#         raw_requirements: Any,
#         *,
#         context: Optional[
#             Mapping[str, Any]
#         ] = None,
#         bearer_token: str | None = None,
#         correlation_id: str | None = None,
#         config: RunnableConfig | None = None,
#     ) -> dict[str, Any]:
#         context_data = dict(
#             context or {}
#         )

#         company_id = (
#             context_data.get("CompanyId")
#             or context_data.get("companyId")
#         )

#         tender_id = (
#             context_data.get("TenderId")
#             or context_data.get("tenderId")
#         )

#         deduplication_id = (
#             context_data.get("DeduplicationId")
#             or correlation_id
#         )

#         requirements = normalize_requirements(
#             raw_requirements
#         )

#         requirement_count = len(
#             requirements
#         )

#         if not requirements:
#             raise ValueError(
#                 "No requirements were supplied to "
#                 "Agent 1."
#             )

#         tracking_token = self._logger.start(
#             message=(
#                 "Requirement deduplication "
#                 "processing started"
#             ),
#             event_type=(
#                 "RequirementDeduplicationStarted"
#             ),
#         )

#         effective_correlation_id = (
#             tracking_token["correlation_id"]
#         )

#         common_payload = {
#             "companyId": company_id,
#             "tenderId": tender_id,
#             "deduplicationId": (
#                 deduplication_id
#             ),
#             "inputRequirementCount": (
#                 requirement_count
#             ),
#         }

#         await asyncio.to_thread(
#             self._logger.log,
#             message=(
#                 "Requirement deduplication "
#                 "processing started"
#             ),
#             event_type=(
#                 "RequirementDeduplicationStarted"
#             ),
#             is_success=True,
#             duration_ms=0,
#             start_time=tracking_token[
#                 "start_time"
#             ],
#             end_time=None,
#             payload=common_payload,
#             correlation_id=(
#                 effective_correlation_id
#             ),
#         )

#         try:
#             index_lookup = {
#                 id(requirement): index
#                 for index, requirement in enumerate(
#                     requirements,
#                     start=1,
#                 )
#             }

#             source_by_id: dict[
#                 str,
#                 Any,
#             ] = {}

#             for index, requirement in enumerate(
#                 requirements,
#                 start=1,
#             ):
#                 source_by_id[
#                     get_requirement_id(
#                         requirement,
#                         index,
#                     )
#                 ] = requirement

#             candidate_components = (
#                 _build_candidate_components(
#                     requirements
#                 )
#             )

#             multi_item_components = sum(
#                 1
#                 for component in (
#                     candidate_components
#                 )
#                 if len(component) > 1
#             )

#             largest_component_size = max(
#                 (
#                     len(component)
#                     for component in (
#                         candidate_components
#                     )
#                 ),
#                 default=0,
#             )

#             print(
#                 "Global deduplication candidates prepared:",
#                 {
#                     "inputRequirementCount": (
#                         requirement_count
#                     ),
#                     "candidateComponentCount": len(
#                         candidate_components
#                     ),
#                     "multiRequirementComponentCount": (
#                         multi_item_components
#                     ),
#                     "largestComponentSize": (
#                         largest_component_size
#                     ),
#                     "maxLlmGroupSize": (
#                         self.max_llm_group_size
#                     ),
#                 },
#             )

#             compact_items: list[
#                 dict[str, Any]
#             ] = []

#             llm_partition_count = 0
#             llm_fallback_count = 0

#             for component_number, component in enumerate(
#                 candidate_components,
#                 start=1,
#             ):
#                 component_requirements = [
#                     requirements[index]
#                     for index in component
#                 ]

#                 partitions = (
#                     self._partition_large_component(
#                         component_requirements
#                     )
#                 )

#                 for partition_number, partition in enumerate(
#                     partitions,
#                     start=1,
#                 ):
#                     partition_items, llm_attempted = (
#                         await self._process_candidate_partition(
#                             partition,
#                             context_data=context_data,
#                             bearer_token=bearer_token,
#                             correlation_id=(
#                                 effective_correlation_id
#                             ),
#                             config=config,
#                             index_lookup=index_lookup,
#                         )
#                     )

#                     if llm_attempted:
#                         llm_partition_count += 1

#                         # A fallback returns exact groups and uniques.
#                         if (
#                             len(partition_items)
#                             == len(partition)
#                             and not any(
#                                 len(
#                                     item.get(
#                                         "RequirementIds",
#                                         [],
#                                     )
#                                 ) > 1
#                                 for item in partition_items
#                             )
#                         ):
#                             llm_fallback_count += 1

#                     compact_items.extend(
#                         partition_items
#                     )

#                     print(
#                         "Candidate partition completed:",
#                         {
#                             "componentNumber": (
#                                 component_number
#                             ),
#                             "partitionNumber": (
#                                 partition_number
#                             ),
#                             "inputCount": len(
#                                 partition
#                             ),
#                             "outputCount": len(
#                                 partition_items
#                             ),
#                             "llmAttempted": (
#                                 llm_attempted
#                             ),
#                         },
#                     )

#             consolidated_items = (
#                 _consolidate_exact_output_items(
#                     compact_items,
#                     source_by_id,
#                     index_lookup=index_lookup,
#                 )
#             )

#             repaired_items = (
#                 _repair_global_coverage(
#                     consolidated_items,
#                     requirements,
#                     index_lookup=index_lookup,
#                 )
#             )

#             final_items = _assign_final_ids(
#                 repaired_items
#             )

#             duplicates_removed = (
#                 requirement_count
#                 - len(final_items)
#             )

#             result = {
#                 "Summary": {
#                     "TotalInputRequirements": (
#                         requirement_count
#                     ),
#                     "TotalDeduplicatedRequirements": (
#                         len(final_items)
#                     ),
#                     "DuplicatesRemoved": (
#                         duplicates_removed
#                     ),
#                 },
#                 "DeduplicatedRequirements": (
#                     final_items
#                 ),
#             }

#             completed_payload = {
#                 **common_payload,
#                 "totalInputRequirements": (
#                     requirement_count
#                 ),
#                 "totalDeduplicatedRequirements": (
#                     len(final_items)
#                 ),
#                 "duplicatesRemoved": (
#                     duplicates_removed
#                 ),
#                 "candidateComponentCount": len(
#                     candidate_components
#                 ),
#                 "llmPartitionCount": (
#                     llm_partition_count
#                 ),
#                 "llmFallbackCount": (
#                     llm_fallback_count
#                 ),
#                 "deduplicationStatus": (
#                     "Completed"
#                 ),
#             }

#             await asyncio.to_thread(
#                 self._logger.end,
#                 tracking_token=tracking_token,
#                 is_success=True,
#                 message=(
#                     "Requirement deduplication "
#                     "completed"
#                 ),
#                 event_type=(
#                     "RequirementDeduplicationCompleted"
#                 ),
#                 payload=completed_payload,
#             )

#             return result

#         except Exception as exc:
#             failed_payload = {
#                 **common_payload,
#                 "error": str(exc),
#                 "errorType": (
#                     type(exc).__name__
#                 ),
#             }

#             await asyncio.to_thread(
#                 self._logger.end,
#                 tracking_token=tracking_token,
#                 is_success=False,
#                 message=(
#                     "Requirement deduplication failed"
#                 ),
#                 event_type=(
#                     "RequirementDeduplicationFailed"
#                 ),
#                 payload=failed_payload,
#             )

#             raise

#     async def run(
#         self,
#         raw_requirements: Any,
#         **kwargs: Any,
#     ) -> dict[str, Any]:
#         return await self.deduplicate(
#             raw_requirements=raw_requirements,
#             **kwargs,
#         )

#     async def process(
#         self,
#         raw_requirements: Any,
#         **kwargs: Any,
#     ) -> dict[str, Any]:
#         return await self.deduplicate(
#             raw_requirements=raw_requirements,
#             **kwargs,
#         )

#     async def ainvoke(
#         self,
#         input_data: Any,
#         config: RunnableConfig | None = None,
#         **kwargs: Any,
#     ) -> dict[str, Any]:
#         return await self.deduplicate(
#             raw_requirements=input_data,
#             config=config,
#             **kwargs,
#         )


# DeduplicationAgent = (
#     RequirementDeduplicationAgent
# )

# Agent = RequirementDeduplicationAgent



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
                    "Completed"
                ),
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