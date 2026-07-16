
# from __future__ import annotations

# import asyncio
# import json
# import os
# import time
# from datetime import datetime, timezone
# from typing import Any, Mapping, Optional, Sequence

# from bson import ObjectId
# from langchain_core.runnables import RunnableConfig
# from langchain_openai import OpenAIEmbeddings
# from qdrant_client import QdrantClient, models

# from app.infrastructure.database import get_database
# from app.infrastructure.load_llms import (
#     create_llm,
#     get_openai_api_key,
# )
# from app.infrastructure.logger import Logging
# from app.infrastructure.token_usage import TokenUsageService


# def utc_now() -> datetime:
#     return datetime.now(timezone.utc)


# def get_environment_value(
#     variable_name: str,
#     default: str = "",
# ) -> str:
#     return str(
#         os.getenv(variable_name, default)
#         or default
#     ).strip()


# def get_required_environment_value(
#     variable_name: str,
# ) -> str:
#     value = get_environment_value(variable_name)

#     if not value:
#         raise ValueError(
#             f"{variable_name} is missing in the .env file"
#         )

#     return value


# def normalize_boolean(value: Any) -> bool:
#     if isinstance(value, bool):
#         return value

#     if value is None:
#         return False

#     if isinstance(value, (int, float)):
#         return value != 0

#     if isinstance(value, str):
#         return value.strip().lower() in {
#             "true",
#             "1",
#             "yes",
#             "y",
#         }

#     return False


# def normalize_string_list(value: Any) -> list[str]:
#     if value is None:
#         return []

#     if isinstance(value, str):
#         values: Sequence[Any] = [value]

#     elif isinstance(value, Sequence) and not isinstance(
#         value,
#         (bytes, bytearray),
#     ):
#         values = value

#     else:
#         values = [value]

#     result: list[str] = []
#     seen: set[str] = set()

#     for item in values:
#         item_text = str(item or "").strip()

#         if not item_text:
#             continue

#         normalized_item = item_text.casefold()

#         if normalized_item in seen:
#             continue

#         seen.add(normalized_item)
#         result.append(item_text)

#     return result


# def get_first_value(
#     source: Any,
#     *keys: str,
#     default: Any = None,
# ) -> Any:
#     if not isinstance(source, Mapping):
#         return default

#     for key in keys:
#         if key in source:
#             value = source.get(key)

#             if value is not None:
#                 return value

#     return default


# def get_nested_value(
#     source: Any,
#     dotted_key: str,
# ) -> Any:
#     current_value = source

#     for key in dotted_key.split("."):
#         if not isinstance(current_value, Mapping):
#             return None

#         current_value = current_value.get(key)

#     return current_value


# def serialize_mongo_value(value: Any) -> Any:
#     if isinstance(value, ObjectId):
#         return str(value)

#     if isinstance(value, datetime):
#         return value.isoformat()

#     if isinstance(value, Mapping):
#         return {
#             str(key): serialize_mongo_value(item)
#             for key, item in value.items()
#         }

#     if isinstance(value, list):
#         return [
#             serialize_mongo_value(item)
#             for item in value
#         ]

#     return value


# def build_id_values(value: str) -> list[Any]:
#     values: list[Any] = [value]

#     if ObjectId.is_valid(value):
#         values.append(ObjectId(value))

#     return values


# def build_company_tender_query(
#     company_id: str,
#     tender_id: str,
# ) -> dict[str, Any]:
#     company_values = build_id_values(company_id)
#     tender_values = build_id_values(tender_id)

#     return {
#         "$and": [
#             {
#                 "$or": [
#                     {
#                         "CompanyId": {
#                             "$in": company_values
#                         }
#                     },
#                     {
#                         "companyId": {
#                             "$in": company_values
#                         }
#                     },
#                     {
#                         "company_id": {
#                             "$in": company_values
#                         }
#                     },
#                 ]
#             },
#             {
#                 "$or": [
#                     {
#                         "TenderId": {
#                             "$in": tender_values
#                         }
#                     },
#                     {
#                         "tenderId": {
#                             "$in": tender_values
#                         }
#                     },
#                     {
#                         "tender_id": {
#                             "$in": tender_values
#                         }
#                     },
#                 ]
#             },
#         ]
#     }


# def extract_deduplicated_requirements(
#     source_document: Mapping[str, Any],
# ) -> list[dict[str, Any]]:
#     candidate_paths = (
#         "Output.DeduplicatedRequirements",
#         "Result.DeduplicatedRequirements",
#         "Output.Result.DeduplicatedRequirements",
#         "DeduplicatedRequirements",
#     )

#     for path in candidate_paths:
#         value = get_nested_value(
#             source_document,
#             path,
#         )

#         if isinstance(value, list):
#             return [
#                 dict(item)
#                 for item in value
#                 if isinstance(item, Mapping)
#             ]

#     return []


# def get_requirement_is_regenerated(
#     requirement: Mapping[str, Any],
# ) -> bool:
#     direct_value = get_first_value(
#         requirement,
#         "IsRegenerated",
#         "isRegenerated",
#         "is_regenerated",
#         default=None,
#     )

#     if direct_value is not None:
#         return normalize_boolean(direct_value)

#     status_value = str(
#         get_first_value(
#             requirement,
#             "Status",
#             "status",
#             default="",
#         )
#         or ""
#     ).strip()

#     if status_value.casefold() == "isregenerating":
#         return True

#     source_requirements = get_first_value(
#         requirement,
#         "SourceRequirements",
#         "sourceRequirements",
#         default=[],
#     )

#     if not isinstance(source_requirements, list):
#         return False

#     return any(
#         normalize_boolean(
#             get_first_value(
#                 source_requirement,
#                 "IsRegenerated",
#                 "isRegenerated",
#                 "is_regenerated",
#                 default=False,
#             )
#         )
#         for source_requirement in source_requirements
#         if isinstance(source_requirement, Mapping)
#     )


# def build_generation_fields(
#     requirement: Mapping[str, Any],
# ) -> dict[str, Any]:
#     is_regenerated = (
#         get_requirement_is_regenerated(
#             requirement
#         )
#     )

#     return {
#         "IsGenerated": True,
#         "IsRegenerated": is_regenerated,
#         "Status": (
#             "IsRegenerating"
#             if is_regenerated
#             else "Active"
#         ),
#     }


# def collect_intent_values(
#     requirement: Mapping[str, Any],
# ) -> dict[str, list[str]]:
#     """
#     Read the evidence-routing metadata produced by Agent 1.

#     Preferred Agent 1 output fields:

#         CapabilityIntent
#         EvidenceSections
#         SemanticAnchors

#     IntentResult and SourceRequirements are retained as fallback
#     sources for backward compatibility.
#     """

#     capability_intents: list[str] = []
#     evidence_sections: list[str] = []
#     semantic_anchors: list[str] = []

#     # Preferred direct Agent 1 output.
#     capability_intents.extend(
#         normalize_string_list(
#             get_first_value(
#                 requirement,
#                 "CapabilityIntent",
#                 "capability_intent",
#                 "capabilityIntent",
#                 default=[],
#             )
#         )
#     )

#     evidence_sections.extend(
#         normalize_string_list(
#             get_first_value(
#                 requirement,
#                 "EvidenceSections",
#                 "evidence_sections",
#                 "evidenceSections",
#                 default=[],
#             )
#         )
#     )

#     semantic_anchors.extend(
#         normalize_string_list(
#             get_first_value(
#                 requirement,
#                 "SemanticAnchors",
#                 "semantic_anchors",
#                 "semanticAnchors",
#                 default=[],
#             )
#         )
#     )

#     intent_sources: list[Mapping[str, Any]] = []

#     direct_intent = get_first_value(
#         requirement,
#         "IntentResult",
#         "intentResult",
#         "intent_result",
#         default=None,
#     )

#     if isinstance(direct_intent, Mapping):
#         intent_sources.append(direct_intent)

#     source_requirements = get_first_value(
#         requirement,
#         "SourceRequirements",
#         "sourceRequirements",
#         default=[],
#     )

#     if isinstance(source_requirements, list):
#         for source_requirement in source_requirements:
#             if not isinstance(
#                 source_requirement,
#                 Mapping,
#             ):
#                 continue

#             # Direct fields on the original requirement.
#             capability_intents.extend(
#                 normalize_string_list(
#                     get_first_value(
#                         source_requirement,
#                         "CapabilityIntent",
#                         "capability_intent",
#                         "capabilityIntent",
#                         default=[],
#                     )
#                 )
#             )

#             evidence_sections.extend(
#                 normalize_string_list(
#                     get_first_value(
#                         source_requirement,
#                         "EvidenceSections",
#                         "evidence_sections",
#                         "evidenceSections",
#                         default=[],
#                     )
#                 )
#             )

#             semantic_anchors.extend(
#                 normalize_string_list(
#                     get_first_value(
#                         source_requirement,
#                         "SemanticAnchors",
#                         "semantic_anchors",
#                         "semanticAnchors",
#                         default=[],
#                     )
#                 )
#             )

#             source_intent = get_first_value(
#                 source_requirement,
#                 "IntentResult",
#                 "intentResult",
#                 "intent_result",
#                 default=None,
#             )

#             if isinstance(source_intent, Mapping):
#                 intent_sources.append(source_intent)

#     for intent_source in intent_sources:
#         capability_intents.extend(
#             normalize_string_list(
#                 get_first_value(
#                     intent_source,
#                     "CapabilityIntent",
#                     "capability_intent",
#                     "capabilityIntent",
#                     default=[],
#                 )
#             )
#         )

#         evidence_sections.extend(
#             normalize_string_list(
#                 get_first_value(
#                     intent_source,
#                     "EvidenceSections",
#                     "evidence_sections",
#                     "evidenceSections",
#                     default=[],
#                 )
#             )
#         )

#         semantic_anchors.extend(
#             normalize_string_list(
#                 get_first_value(
#                     intent_source,
#                     "SemanticAnchors",
#                     "semantic_anchors",
#                     "semanticAnchors",
#                     default=[],
#                 )
#             )
#         )

#     return {
#         "CapabilityIntent": normalize_string_list(
#             capability_intents
#         ),
#         "EvidenceSections": normalize_string_list(
#             evidence_sections
#         ),
#         "SemanticAnchors": normalize_string_list(
#             semantic_anchors
#         ),
#     }


# def build_evidence_search_query(
#     canonical_requirement: str,
#     intent_values: Mapping[str, Any],
# ) -> str:
#     """
#     Build the semantic-search query sent to Qdrant.

#     SemanticAnchors are placed first because they are the primary
#     evidence-retrieval terms produced by Agent 1. The requirement and
#     routing context are retained to disambiguate short anchors.
#     """

#     capability_intents = normalize_string_list(
#         intent_values.get("CapabilityIntent")
#     )

#     evidence_sections = normalize_string_list(
#         intent_values.get("EvidenceSections")
#     )

#     semantic_anchors = normalize_string_list(
#         intent_values.get("SemanticAnchors")
#     )

#     query_parts: list[str] = []

#     if semantic_anchors:
#         query_parts.append(
#             "Primary semantic anchors: "
#             + ", ".join(semantic_anchors)
#         )

#     query_parts.append(
#         f"Tender requirement: {canonical_requirement}"
#     )

#     if capability_intents:
#         query_parts.append(
#             "Capability intent: "
#             + ", ".join(capability_intents)
#         )

#     if evidence_sections:
#         query_parts.append(
#             "Expected evidence sections: "
#             + ", ".join(evidence_sections)
#         )

#     search_query = "\n".join(query_parts)

#     print(
#         "Evidence search terms prepared:",
#         {
#             "SemanticAnchors": semantic_anchors,
#             "CapabilityIntent": capability_intents,
#             "EvidenceSections": evidence_sections,
#             "queryLength": len(search_query),
#         },
#     )

#     return search_query


# def extract_payload_text(
#     payload: Mapping[str, Any],
# ) -> str:
#     text_paths = (
#         "ChunkText",
#         "chunkText",
#         "chunk_text",
#         "Text",
#         "text",
#         "Content",
#         "content",
#         "page_content",
#         "PageContent",
#         "document",
#         "Document",
#         "metadata.ChunkText",
#         "metadata.chunkText",
#         "metadata.chunk_text",
#         "metadata.Text",
#         "metadata.text",
#         "metadata.Content",
#         "metadata.content",
#         "metadata.page_content",
#     )

#     for path in text_paths:
#         value = get_nested_value(payload, path)

#         if isinstance(value, str) and value.strip():
#             return value.strip()

#     return ""


# def extract_payload_metadata(
#     payload: Mapping[str, Any],
#     *paths: str,
# ) -> str:
#     for path in paths:
#         value = get_nested_value(payload, path)

#         if value is None:
#             continue

#         value_text = str(value).strip()

#         if value_text:
#             return value_text

#     return ""


# def parse_llm_json_response(response: Any) -> dict[str, Any]:
#     content = getattr(response, "content", response)

#     if isinstance(content, list):
#         content_parts: list[str] = []

#         for item in content:
#             if isinstance(item, Mapping):
#                 item_text = (
#                     item.get("text")
#                     or item.get("content")
#                     or ""
#                 )
#             else:
#                 item_text = str(item)

#             if str(item_text).strip():
#                 content_parts.append(
#                     str(item_text).strip()
#                 )

#         content_text = "\n".join(content_parts)

#     else:
#         content_text = str(content or "").strip()

#     if not content_text:
#         raise ValueError(
#             "The LLM returned an empty evidence-summary response."
#         )

#     cleaned_text = content_text.strip()

#     if cleaned_text.startswith("```"):
#         cleaned_text = cleaned_text.strip("`").strip()

#         if cleaned_text.lower().startswith("json"):
#             cleaned_text = cleaned_text[4:].strip()

#     first_brace = cleaned_text.find("{")
#     last_brace = cleaned_text.rfind("}")

#     if first_brace >= 0 and last_brace > first_brace:
#         cleaned_text = cleaned_text[
#             first_brace:last_brace + 1
#         ]

#     try:
#         parsed = json.loads(cleaned_text)

#     except json.JSONDecodeError as exc:
#         raise ValueError(
#             "The LLM evidence-summary response was not valid JSON. "
#             f"Response: {content_text[:1000]}"
#         ) from exc

#     if not isinstance(parsed, Mapping):
#         raise ValueError(
#             "The LLM evidence-summary response must be a JSON object."
#         )

#     return dict(parsed)


# def build_evidence_summary_prompt(
#     canonical_requirement: str,
#     intent_values: Mapping[str, Any],
#     evidence_sources: list[dict[str, Any]],
# ) -> str:
#     """
#     Build the LLM prompt for one deduplicated requirement.

#     The LLM receives only the selected Qdrant evidence chunks and
#     returns the compact evidence decision fields required by MongoDB.
#     """

#     evidence_blocks: list[str] = []

#     for evidence_index, evidence_source in enumerate(
#         evidence_sources,
#         start=1,
#     ):
#         evidence_blocks.append(
#             "\n".join(
#                 [
#                     f"[Evidence {evidence_index}]",
#                     (
#                         "EvidenceId: "
#                         f"{evidence_source.get('EvidenceId', '')}"
#                     ),
#                     (
#                         "ChunkId: "
#                         f"{evidence_source.get('ChunkId', '')}"
#                     ),
#                     (
#                         "SourceTitle: "
#                         f"{evidence_source.get('SourceTitle', '')}"
#                     ),
#                     (
#                         "SourceDocument: "
#                         f"{evidence_source.get('SourceDocument', '')}"
#                     ),
#                     (
#                         "DocumentType: "
#                         f"{evidence_source.get('DocumentType', '')}"
#                     ),
#                     (
#                         "RelatedSection: "
#                         f"{evidence_source.get('RelatedSection', '')}"
#                     ),
#                     (
#                         "EvidenceScore: "
#                         f"{evidence_source.get('EvidenceScore', 0)}"
#                     ),
#                     "EvidenceText:",
#                     str(
#                         evidence_source.get(
#                             "EvidenceText",
#                             "",
#                         )
#                     ),
#                 ]
#             )
#         )

#     evidence_text = "\n\n".join(
#         evidence_blocks
#     )

#     return f"""
# You are the Evidence Summary Agent for a tender-response system.

# Evaluate whether the retrieved company evidence supports the tender requirement.

# STRICT RULES:
# 1. Use only the supplied evidence chunks.
# 2. Do not invent clients, projects, certifications, figures, dates, technologies, outcomes or capabilities.
# 3. EvidenceFound must be true only when the supplied chunks materially support the requirement.
# 4. EvidenceReason must briefly explain why the evidence supports or does not support the requirement.
# 5. EvidenceSummary must be concise and grounded only in the supplied evidence.
# 6. MissingEvidenceReason must be null when EvidenceFound is true.
# 7. When EvidenceFound is false, EvidenceSummary must be an empty string and MissingEvidenceReason must clearly state what evidence is missing.
# 8. EvidenceConfidence must be a number between 0 and 1.
# 9. Return valid JSON only. Do not return markdown or code fences.

# TENDER REQUIREMENT:
# {canonical_requirement}

# CAPABILITY INTENT:
# {json.dumps(intent_values.get('CapabilityIntent', []), ensure_ascii=False)}

# EXPECTED EVIDENCE SECTIONS:
# {json.dumps(intent_values.get('EvidenceSections', []), ensure_ascii=False)}

# SEMANTIC ANCHORS:
# {json.dumps(intent_values.get('SemanticAnchors', []), ensure_ascii=False)}

# RETRIEVED COMPANY EVIDENCE:
# {evidence_text}

# Return exactly this JSON structure:
# {{
#   "EvidenceFound": true,
#   "EvidenceReason": "Why the supplied evidence does or does not support the requirement.",
#   "EvidenceSummary": "Concise evidence summary grounded only in the supplied chunks.",
#   "EvidenceConfidence": 0.0,
#   "MissingEvidenceReason": null
# }}
# """.strip()


# class RequirementEvidenceSummaryAgent:
#     """
#     Evidence Summary Agent.

#     Complete flow contained in this one file:

#     1. Read the latest successfully regenerated Requirement
#        Deduplication result from MongoDB.
#     2. Extract Output.DeduplicatedRequirements[].
#     3. Search company-specific evidence chunks in Qdrant.
#     4. Send each requirement and its retrieved chunks to the LLM.
#     5. Save the Evidence Summary output in MongoDB.
#     """

#     def __init__(
#         self,
#         llm: Any | None = None,
#         embeddings: Any | None = None,
#         qdrant_client: QdrantClient | None = None,
#     ) -> None:
#         self._llm = llm
#         self._embeddings = embeddings
#         self._qdrant_client = qdrant_client
#         self._resolved_qdrant_url: str | None = None
#         self._resolved_qdrant_vector_name: str | None = None
#         self._resolved_qdrant_vector_size: int | None = None

#         self._logger = Logging(
#             agent_name="Evidence Summary Agent",
#             source_module=(
#                 "app.agents."
#                 "Evidence_Summary_Agent.Agent"
#             ),
#         )

#     @property
#     def llm(self) -> Any:
#         if self._llm is None:
#             self._llm = create_llm()

#         return self._llm

#     @property
#     def embeddings(self) -> Any:
#         if self._embeddings is None:
#             embedding_model = get_environment_value(
#                 "EMBEDDING_MODEL",
#                 "text-embedding-3-small",
#             )

#             self._embeddings = OpenAIEmbeddings(
#                 model=embedding_model,
#                 api_key=get_openai_api_key(),
#             )

#         return self._embeddings

#     @staticmethod
#     def normalize_qdrant_url(
#         value: str,
#     ) -> str:
#         """
#         Normalize a Qdrant server base URL.

#         Correct example:

#             http://localhost:6333

#         Do not include /dashboard or /collections.
#         """

#         normalized_url = str(
#             value or ""
#         ).strip().rstrip("/")

#         removable_suffixes = (
#             "/dashboard",
#             "/collections",
#         )

#         for suffix in removable_suffixes:
#             if normalized_url.lower().endswith(
#                 suffix
#             ):
#                 normalized_url = normalized_url[
#                     :-len(suffix)
#                 ].rstrip("/")
#                 break

#         return normalized_url

#     def get_qdrant_candidate_urls(
#         self,
#     ) -> list[str]:
#         """
#         Build the ordered list of Qdrant URLs to try.

#         QDRANT_URL is tried first.

#         QDRANT_FALLBACK_URL is tried second and defaults to:

#             http://localhost:6333
#         """

#         configured_url = (
#             get_required_environment_value(
#                 "QDRANT_URL"
#             )
#         )

#         fallback_url = get_environment_value(
#             "QDRANT_FALLBACK_URL",
#             "http://localhost:6333",
#         )

#         candidate_urls: list[str] = []

#         for raw_url in (
#             configured_url,
#             fallback_url,
#         ):
#             normalized_url = (
#                 self.normalize_qdrant_url(
#                     raw_url
#                 )
#             )

#             if not normalized_url:
#                 continue

#             if normalized_url in candidate_urls:
#                 continue

#             candidate_urls.append(
#                 normalized_url
#             )

#         return candidate_urls

#     def create_qdrant_client(
#         self,
#         *,
#         qdrant_url: str,
#         qdrant_api_key: str,
#         qdrant_timeout: float,
#     ) -> QdrantClient:
#         """
#         Create a Qdrant client.

#         check_compatibility=False suppresses the version warning.
#         Older qdrant-client versions are supported through fallback.
#         """

#         client_arguments: dict[str, Any] = {
#             "url": qdrant_url,
#             "api_key": (
#                 qdrant_api_key
#                 if qdrant_api_key
#                 else None
#             ),
#             "timeout": qdrant_timeout,
#         }

#         try:
#             return QdrantClient(
#                 **client_arguments,
#                 check_compatibility=False,
#             )

#         except TypeError:
#             return QdrantClient(
#                 **client_arguments
#             )

#     @staticmethod
#     def get_qdrant_vector_size(
#         vector_parameters: Any,
#     ) -> int | None:
#         """
#         Read the vector size from either a Qdrant model or a plain
#         dictionary.
#         """

#         if vector_parameters is None:
#             return None

#         if isinstance(vector_parameters, Mapping):
#             raw_size = vector_parameters.get("size")

#         else:
#             raw_size = getattr(
#                 vector_parameters,
#                 "size",
#                 None,
#             )

#         if raw_size is None:
#             return None

#         try:
#             return int(raw_size)

#         except (TypeError, ValueError):
#             return None

#     def resolve_qdrant_vector_configuration(
#         self,
#         collection_info: Any,
#     ) -> tuple[str | None, int | None]:
#         """
#         Resolve whether CPDocuments uses an unnamed dense vector or
#         one or more named dense vectors.

#         QDRANT_VECTOR_NAME is used when explicitly configured.
#         When the collection has exactly one named dense vector, that
#         name is selected automatically.
#         """

#         collection_config = getattr(
#             collection_info,
#             "config",
#             None,
#         )

#         collection_params = getattr(
#             collection_config,
#             "params",
#             None,
#         )

#         vectors_config = getattr(
#             collection_params,
#             "vectors",
#             None,
#         )

#         # Fallback for responses represented as dictionaries.
#         if vectors_config is None:
#             if hasattr(collection_info, "model_dump"):
#                 try:
#                     collection_data = (
#                         collection_info.model_dump()
#                     )
#                 except Exception:
#                     collection_data = {}

#             elif isinstance(collection_info, Mapping):
#                 collection_data = dict(
#                     collection_info
#                 )

#             else:
#                 collection_data = {}

#             vectors_config = (
#                 collection_data
#                 .get("config", {})
#                 .get("params", {})
#                 .get("vectors")
#             )

#         configured_vector_name = (
#             get_environment_value(
#                 "QDRANT_VECTOR_NAME"
#             )
#         )

#         # A dictionary means this collection uses named vectors.
#         if isinstance(vectors_config, Mapping):
#             available_vector_names = [
#                 str(vector_name)
#                 for vector_name in vectors_config.keys()
#                 if str(vector_name).strip()
#             ]

#             if not available_vector_names:
#                 raise RuntimeError(
#                     "Qdrant collection does not contain a dense "
#                     "vector configuration. Available named dense "
#                     "vectors are empty."
#                 )

#             if configured_vector_name:
#                 if (
#                     configured_vector_name
#                     not in available_vector_names
#                 ):
#                     raise RuntimeError(
#                         "Configured QDRANT_VECTOR_NAME does not "
#                         "exist in the Qdrant collection. "
#                         f"Configured: "
#                         f"'{configured_vector_name}'. "
#                         f"Available: "
#                         f"{available_vector_names}."
#                     )

#                 selected_vector_name = (
#                     configured_vector_name
#                 )

#             elif len(available_vector_names) == 1:
#                 selected_vector_name = (
#                     available_vector_names[0]
#                 )

#             else:
#                 preferred_names = (
#                     "default",
#                     "text",
#                     "content",
#                     "embedding",
#                     "dense",
#                     "vector",
#                 )

#                 selected_vector_name = next(
#                     (
#                         preferred_name
#                         for preferred_name
#                         in preferred_names
#                         if preferred_name
#                         in available_vector_names
#                     ),
#                     None,
#                 )

#                 if selected_vector_name is None:
#                     raise RuntimeError(
#                         "Qdrant collection contains multiple named "
#                         "vectors and no unambiguous vector can be "
#                         "selected. Set QDRANT_VECTOR_NAME in .env. "
#                         f"Available vector names: "
#                         f"{available_vector_names}."
#                     )

#             selected_parameters = vectors_config[
#                 selected_vector_name
#             ]

#             selected_vector_size = (
#                 self.get_qdrant_vector_size(
#                     selected_parameters
#                 )
#             )

#             return (
#                 selected_vector_name,
#                 selected_vector_size,
#             )

#         # A single VectorParams object means the collection uses the
#         # unnamed/default dense vector.
#         selected_vector_size = (
#             self.get_qdrant_vector_size(
#                 vectors_config
#             )
#         )

#         if configured_vector_name:
#             raise RuntimeError(
#                 "QDRANT_VECTOR_NAME is configured as "
#                 f"'{configured_vector_name}', but the collection "
#                 "uses an unnamed/default dense vector. Remove "
#                 "QDRANT_VECTOR_NAME from .env."
#             )

#         if vectors_config is None:
#             raise RuntimeError(
#                 "Unable to read the dense-vector configuration "
#                 "from the Qdrant collection."
#             )

#         return (
#             None,
#             selected_vector_size,
#         )

#     @property
#     def qdrant_client(self) -> QdrantClient:
#         """
#         Resolve and cache a working Qdrant client.

#         A URL is accepted only when the configured collection exists.
#         This prevents frontend URLs such as localhost:5173 from being
#         treated as Qdrant servers.
#         """

#         if self._qdrant_client is not None:
#             return self._qdrant_client

#         qdrant_api_key = get_environment_value(
#             "QDRANT_API_KEY"
#         )

#         qdrant_timeout = float(
#             get_environment_value(
#                 "QDRANT_TIMEOUT",
#                 "60",
#             )
#         )

#         candidate_urls = (
#             self.get_qdrant_candidate_urls()
#         )

#         attempt_errors: list[
#             dict[str, Any]
#         ] = []

#         for candidate_url in candidate_urls:
#             candidate_client: (
#                 QdrantClient | None
#             ) = None

#             print(
#                 "Testing Qdrant configuration:",
#                 {
#                     "url": candidate_url,
#                     "collection": (
#                         self.qdrant_collection_name
#                     ),
#                     "apiKeyPresent": bool(
#                         qdrant_api_key
#                     ),
#                     "timeoutSeconds": (
#                         qdrant_timeout
#                     ),
#                 },
#             )

#             try:
#                 candidate_client = (
#                     self.create_qdrant_client(
#                         qdrant_url=candidate_url,
#                         qdrant_api_key=(
#                             qdrant_api_key
#                         ),
#                         qdrant_timeout=(
#                             qdrant_timeout
#                         ),
#                     )
#                 )

#                 collection_info = (
#                     candidate_client.get_collection(
#                         collection_name=(
#                             self.qdrant_collection_name
#                         )
#                     )
#                 )

#                 (
#                     resolved_vector_name,
#                     resolved_vector_size,
#                 ) = (
#                     self.resolve_qdrant_vector_configuration(
#                         collection_info
#                     )
#                 )

#                 self._qdrant_client = (
#                     candidate_client
#                 )

#                 self._resolved_qdrant_url = (
#                     candidate_url
#                 )

#                 self._resolved_qdrant_vector_name = (
#                     resolved_vector_name
#                 )

#                 self._resolved_qdrant_vector_size = (
#                     resolved_vector_size
#                 )

#                 print(
#                     "Qdrant server selected:",
#                     {
#                         "url": candidate_url,
#                         "collection": (
#                             self.qdrant_collection_name
#                         ),
#                         "status": str(
#                             getattr(
#                                 collection_info,
#                                 "status",
#                                 "available",
#                             )
#                         ),
#                         "vectorName": (
#                             resolved_vector_name
#                             if resolved_vector_name
#                             else "<unnamed>"
#                         ),
#                         "vectorSize": (
#                             resolved_vector_size
#                         ),
#                     },
#                 )

#                 return self._qdrant_client

#             except Exception as exc:
#                 status_code = getattr(
#                     exc,
#                     "status_code",
#                     None,
#                 )

#                 attempt_error = {
#                     "url": candidate_url,
#                     "errorType": (
#                         type(exc).__name__
#                     ),
#                     "statusCode": status_code,
#                     "message": str(exc),
#                 }

#                 attempt_errors.append(
#                     attempt_error
#                 )

#                 print(
#                     "Qdrant candidate rejected:",
#                     attempt_error,
#                 )

#                 if candidate_client is not None:
#                     try:
#                         candidate_client.close()
#                     except Exception:
#                         pass

#         attempted_urls = ", ".join(
#             candidate_urls
#         )

#         raise RuntimeError(
#             "Unable to connect to a Qdrant server "
#             f"containing collection "
#             f"'{self.qdrant_collection_name}'. "
#             f"Attempted URLs: {attempted_urls}. "
#             "Set QDRANT_URL or QDRANT_FALLBACK_URL "
#             "to the Qdrant REST base URL, normally "
#             "http://localhost:6333. "
#             f"Attempt details: {attempt_errors}"
#         )

#     @property
#     def database(self) -> Any:
#         return get_database()

#     @property
#     def source_collection(self) -> Any:
#         collection_name = get_environment_value(
#             "DEDUPLICATION_COLLECTION_NAME",
#             "TenderRequirementDeduplications",
#         )

#         return self.database[collection_name]

#     @property
#     def destination_collection(self) -> Any:
#         collection_name = get_environment_value(
#             "EVIDENCE_SUMMARY_COLLECTION_NAME",
#             "TenderEvidenceSummaries",
#         )

#         return self.database[collection_name]

#     @property
#     def qdrant_collection_name(self) -> str:
#         return get_environment_value(
#             "QDRANT_COLLECTION_NAME",
#             "CPDocuments",
#         )

#     @property
#     def top_k(self) -> int:
#         return max(
#             1,
#             int(
#                 get_environment_value(
#                     "EVIDENCE_TOP_K",
#                     "5",
#                 )
#             ),
#         )

#     @property
#     def score_threshold(self) -> float:
#         return float(
#             get_environment_value(
#                 "EVIDENCE_SCORE_THRESHOLD",
#                 "0.55",
#             )
#         )

#     @property
#     def max_concurrency(self) -> int:
#         return max(
#             1,
#             int(
#                 get_environment_value(
#                     "EVIDENCE_MAX_CONCURRENCY",
#                     "3",
#                 )
#             ),
#         )

#     @property
#     def chunk_character_limit(self) -> int:
#         return max(
#             500,
#             int(
#                 get_environment_value(
#                     "EVIDENCE_CHUNK_CHARACTER_LIMIT",
#                     "4000",
#                 )
#             ),
#         )

#     @property
#     def total_context_character_limit(self) -> int:
#         return max(
#             self.chunk_character_limit,
#             int(
#                 get_environment_value(
#                     "EVIDENCE_TOTAL_CONTEXT_CHARACTER_LIMIT",
#                     "16000",
#                 )
#             ),
#         )

#     async def read_latest_deduplication_document(
#         self,
#         company_id: str,
#         tender_id: str,
#     ) -> dict[str, Any]:
#         query = build_company_tender_query(
#             company_id=company_id,
#             tender_id=tender_id,
#         )

#         query["$and"].append(
#             {
#                 "Status": "IsRegenerated"
#             }
#         )

#         print(
#             "Evidence source database:",
#             self.source_collection.database.name,
#         )

#         print(
#             "Evidence source collection:",
#             self.source_collection.name,
#         )

#         print(
#             "Evidence source query:",
#             query,
#         )

#         source_document = await asyncio.to_thread(
#             self.source_collection.find_one,
#             query,
#             sort=[
#                 ("CompletedAt", -1),
#                 ("_id", -1),
#             ],
#         )

#         if source_document is None:
#             raise ValueError(
#                 "No IsRegenerated deduplication document was found "
#                 "for the supplied CompanyId and TenderId. "
#                 f"CompanyId: {company_id}. "
#                 f"TenderId: {tender_id}."
#             )

#         deduplicated_requirements = (
#             extract_deduplicated_requirements(
#                 source_document
#             )
#         )

#         if not deduplicated_requirements:
#             raise ValueError(
#                 "The IsRegenerated deduplication document does not "
#                 "contain Output.DeduplicatedRequirements[]."
#             )

#         print(
#             "Deduplicated requirements found:",
#             len(deduplicated_requirements),
#         )

#         return source_document

#     def build_qdrant_company_filter(
#         self,
#         company_id: str,
#     ) -> models.Filter:
#         company_field_paths = (
#             "CompanyId",
#             "companyId",
#             "company_id",
#             "metadata.CompanyId",
#             "metadata.companyId",
#             "metadata.company_id",
#         )

#         return models.Filter(
#             should=[
#                 models.FieldCondition(
#                     key=field_path,
#                     match=models.MatchValue(
#                         value=company_id
#                     ),
#                 )
#                 for field_path in company_field_paths
#             ]
#         )

#     async def validate_qdrant_collection(
#         self,
#     ) -> None:
#         """
#         Validate the selected Qdrant connection and collection once
#         before starting concurrent requirement processing.
#         """

#         def validate() -> None:
#             try:
#                 collection_info = (
#                     self.qdrant_client.get_collection(
#                         collection_name=(
#                             self.qdrant_collection_name
#                         )
#                     )
#                 )

#             except Exception as exc:
#                 status_code = getattr(
#                     exc,
#                     "status_code",
#                     None,
#                 )

#                 raise RuntimeError(
#                     "Qdrant collection validation failed. "
#                     f"URL: "
#                     f"{self._resolved_qdrant_url or 'unresolved'}. "
#                     f"Collection: "
#                     f"{self.qdrant_collection_name}. "
#                     f"Status code: {status_code}. "
#                     f"Message: {exc}"
#                 ) from exc

#             print(
#                 "Qdrant collection validated:",
#                 {
#                     "url": (
#                         self._resolved_qdrant_url
#                     ),
#                     "collection": (
#                         self.qdrant_collection_name
#                     ),
#                     "status": str(
#                         getattr(
#                             collection_info,
#                             "status",
#                             "available",
#                         )
#                     ),
#                     "vectorName": (
#                         self._resolved_qdrant_vector_name
#                         if self._resolved_qdrant_vector_name
#                         else "<unnamed>"
#                     ),
#                     "vectorSize": (
#                         self._resolved_qdrant_vector_size
#                     ),
#                 },
#             )

#         await asyncio.to_thread(validate)

#     async def create_query_embedding(
#         self,
#         search_query: str,
#     ) -> list[float]:
#         try:
#             embedding = await asyncio.to_thread(
#                 self.embeddings.embed_query,
#                 search_query,
#             )

#             print(
#                 "Embedding generated successfully:",
#                 {
#                     "dimension": len(
#                         embedding
#                     ),
#                     "queryLength": len(
#                         search_query
#                     ),
#                 },
#             )

#             expected_vector_size = (
#                 self._resolved_qdrant_vector_size
#             )

#             if (
#                 expected_vector_size is not None
#                 and len(embedding)
#                 != expected_vector_size
#             ):
#                 raise RuntimeError(
#                     "Embedding dimension does not match the "
#                     "Qdrant collection vector dimension. "
#                     f"Embedding dimension: {len(embedding)}. "
#                     f"Qdrant dimension: "
#                     f"{expected_vector_size}. "
#                     "Use the same embedding model that was used "
#                     "when CPDocuments was populated."
#                 )

#             return embedding

#         except Exception as exc:
#             print(
#                 "Embedding generation failed:",
#                 {
#                     "errorType": type(exc).__name__,
#                     "statusCode": getattr(
#                         exc,
#                         "status_code",
#                         None,
#                     ),
#                     "errorCode": getattr(
#                         exc,
#                         "code",
#                         None,
#                     ),
#                     "message": str(exc),
#                 },
#             )

#             raise

#     async def search_qdrant(
#         self,
#         company_id: str,
#         search_query: str,
#     ) -> list[Any]:
#         query_vector = await self.create_query_embedding(
#             search_query
#         )

#         company_filter = (
#             self.build_qdrant_company_filter(
#                 company_id
#             )
#         )

#         # The name was resolved from the live collection during
#         # validation. None means the collection uses the unnamed
#         # default vector.
#         vector_name = (
#             self._resolved_qdrant_vector_name
#         )

#         def execute_search() -> list[Any]:
#             client = self.qdrant_client

#             def execute_legacy_search() -> list[Any]:
#                 if not hasattr(client, "search"):
#                     raise TypeError(
#                         "The installed qdrant-client does not "
#                         "provide search()."
#                     )

#                 search_arguments: dict[str, Any] = {
#                     "collection_name": (
#                         self.qdrant_collection_name
#                     ),
#                     "query_vector": query_vector,
#                     "query_filter": company_filter,
#                     "limit": self.top_k,
#                     "with_payload": True,
#                 }

#                 if self.score_threshold > 0:
#                     search_arguments[
#                         "score_threshold"
#                     ] = self.score_threshold

#                 if vector_name:
#                     search_arguments[
#                         "query_vector"
#                     ] = (
#                         vector_name,
#                         query_vector,
#                     )

#                 return list(
#                     client.search(
#                         **search_arguments
#                     )
#                     or []
#                 )

#             if hasattr(client, "query_points"):
#                 query_arguments: dict[str, Any] = {
#                     "collection_name": (
#                         self.qdrant_collection_name
#                     ),
#                     "query": query_vector,
#                     "query_filter": company_filter,
#                     "limit": self.top_k,
#                     "with_payload": True,
#                 }

#                 if self.score_threshold > 0:
#                     query_arguments[
#                         "score_threshold"
#                     ] = self.score_threshold

#                 if vector_name:
#                     query_arguments["using"] = (
#                         vector_name
#                     )

#                 try:
#                     query_response = (
#                         client.query_points(
#                             **query_arguments
#                         )
#                     )

#                     points = getattr(
#                         query_response,
#                         "points",
#                         query_response,
#                     )

#                     return list(points or [])

#                 except Exception as query_exc:
#                     query_status_code = getattr(
#                         query_exc,
#                         "status_code",
#                         None,
#                     )

#                     query_error_message = str(
#                         query_exc
#                     )

#                     query_endpoint_missing = (
#                         query_status_code == 404
#                         or "404" in query_error_message
#                     )

#                     if (
#                         query_endpoint_missing
#                         and hasattr(client, "search")
#                     ):
#                         print(
#                             "Qdrant query_points endpoint "
#                             "returned 404. Falling back "
#                             "to search()."
#                         )

#                         return execute_legacy_search()

#                     raise

#             if hasattr(client, "search"):
#                 return execute_legacy_search()

#             raise TypeError(
#                 "The installed qdrant-client does not support "
#                 "query_points() or search()."
#             )

#         try:
#             print(
#                 "Starting Qdrant search:",
#                 {
#                     "collection": (
#                         self.qdrant_collection_name
#                     ),
#                     "topK": self.top_k,
#                     "scoreThreshold": (
#                         self.score_threshold
#                     ),
#                     "companyId": company_id,
#                     "vectorName": (
#                         vector_name
#                         if vector_name
#                         else "<unnamed>"
#                     ),
#                     "vectorSize": len(
#                         query_vector
#                     ),
#                 },
#             )

#             results = await asyncio.to_thread(
#                 execute_search
#             )

#             print(
#                 "Qdrant search completed:",
#                 {
#                     "resultCount": len(results),
#                 },
#             )

#             return results

#         except Exception as exc:
#             print(
#                 "Qdrant search failed:",
#                 {
#                     "errorType": type(exc).__name__,
#                     "statusCode": getattr(
#                         exc,
#                         "status_code",
#                         None,
#                     ),
#                     "message": str(exc),
#                 },
#             )

#             raise RuntimeError(
#                 "Qdrant search failed. "
#                 f"Error type: "
#                 f"{type(exc).__name__}. "
#                 f"Message: {exc}"
#             ) from exc

#     async def run_qdrant_preflight(
#         self,
#         *,
#         company_id: str,
#         requirements: list[dict[str, Any]],
#     ) -> None:
#         """
#         Execute one real embedding and Qdrant search before creating
#         all evidence tasks.

#         This catches vector-name, vector-dimension, endpoint and
#         filter errors once, instead of repeating them for every
#         requirement.
#         """

#         if not requirements:
#             raise ValueError(
#                 "Qdrant preflight cannot run because no "
#                 "deduplicated requirements were supplied."
#             )

#         first_requirement = requirements[0]

#         canonical_requirement = str(
#             get_first_value(
#                 first_requirement,
#                 "CanonicalRequirement",
#                 "canonicalRequirement",
#                 "RequirementText",
#                 "requirementText",
#                 default="",
#             )
#             or ""
#         ).strip()

#         if not canonical_requirement:
#             raise ValueError(
#                 "The first deduplicated requirement is missing "
#                 "CanonicalRequirement."
#             )

#         intent_values = collect_intent_values(
#             first_requirement
#         )

#         search_query = build_evidence_search_query(
#             canonical_requirement=canonical_requirement,
#             intent_values=intent_values,
#         )

#         await self.search_qdrant(
#             company_id=company_id,
#             search_query=search_query,
#         )

#         print(
#             "Qdrant preflight completed successfully:",
#             {
#                 "url": self._resolved_qdrant_url,
#                 "collection": (
#                     self.qdrant_collection_name
#                 ),
#                 "vectorName": (
#                     self._resolved_qdrant_vector_name
#                     if self._resolved_qdrant_vector_name
#                     else "<unnamed>"
#                 ),
#                 "vectorSize": (
#                     self._resolved_qdrant_vector_size
#                 ),
#             },
#         )

#     def normalize_qdrant_results(
#         self,
#         points: list[Any],
#     ) -> list[dict[str, Any]]:
#         """
#         Convert raw Qdrant points into the compact evidence-source
#         structure stored in MongoDB and supplied to the LLM.
#         """

#         normalized_results: list[
#             dict[str, Any]
#         ] = []

#         total_characters = 0

#         for point in points:
#             payload = getattr(
#                 point,
#                 "payload",
#                 {},
#             ) or {}

#             if not isinstance(payload, Mapping):
#                 payload = {}

#             evidence_text = extract_payload_text(
#                 payload
#             )

#             if not evidence_text:
#                 continue

#             remaining_characters = (
#                 self.total_context_character_limit
#                 - total_characters
#             )

#             if remaining_characters <= 0:
#                 break

#             allowed_characters = min(
#                 self.chunk_character_limit,
#                 remaining_characters,
#             )

#             evidence_text = evidence_text[
#                 :allowed_characters
#             ]

#             total_characters += len(
#                 evidence_text
#             )

#             point_id = getattr(
#                 point,
#                 "id",
#                 "",
#             )

#             point_score = getattr(
#                 point,
#                 "score",
#                 0,
#             )

#             document_id = extract_payload_metadata(
#                 payload,
#                 "DocumentId",
#                 "documentId",
#                 "document_id",
#                 "metadata.DocumentId",
#                 "metadata.documentId",
#                 "metadata.document_id",
#             )

#             source_title = extract_payload_metadata(
#                 payload,
#                 "SourceTitle",
#                 "sourceTitle",
#                 "source_title",
#                 "Title",
#                 "title",
#                 "DocumentTitle",
#                 "documentTitle",
#                 "Heading",
#                 "heading",
#                 "metadata.SourceTitle",
#                 "metadata.sourceTitle",
#                 "metadata.title",
#                 "metadata.Heading",
#                 "metadata.heading",
#             )

#             source_document = extract_payload_metadata(
#                 payload,
#                 "SourceDocument",
#                 "sourceDocument",
#                 "source_document",
#                 "DocumentName",
#                 "documentName",
#                 "FileName",
#                 "fileName",
#                 "file_name",
#                 "SourceFileName",
#                 "sourceFileName",
#                 "metadata.SourceDocument",
#                 "metadata.DocumentName",
#                 "metadata.FileName",
#                 "metadata.fileName",
#                 "metadata.file_name",
#                 "metadata.source",
#             )

#             if not source_document:
#                 source_document = document_id

#             normalized_results.append(
#                 {
#                     "EvidenceId": str(
#                         point_id
#                     ),
#                     "ChunkId": extract_payload_metadata(
#                         payload,
#                         "ChunkId",
#                         "chunkId",
#                         "chunk_id",
#                         "metadata.ChunkId",
#                         "metadata.chunkId",
#                         "metadata.chunk_id",
#                     ),
#                     "SourceTitle": source_title,
#                     "SourceDocument": (
#                         source_document
#                     ),
#                     "DocumentType": (
#                         extract_payload_metadata(
#                             payload,
#                             "DocumentType",
#                             "documentType",
#                             "document_type",
#                             "FileType",
#                             "fileType",
#                             "file_type",
#                             "Type",
#                             "type",
#                             "metadata.DocumentType",
#                             "metadata.documentType",
#                             "metadata.FileType",
#                             "metadata.type",
#                         )
#                     ),
#                     "RelatedSection": (
#                         extract_payload_metadata(
#                             payload,
#                             "RelatedSection",
#                             "relatedSection",
#                             "related_section",
#                             "Section",
#                             "section",
#                             "SectionName",
#                             "sectionName",
#                             "Heading",
#                             "heading",
#                             "metadata.RelatedSection",
#                             "metadata.Section",
#                             "metadata.section",
#                             "metadata.SectionName",
#                             "metadata.sectionName",
#                             "metadata.Heading",
#                             "metadata.heading",
#                         )
#                     ),
#                     "EvidenceText": evidence_text,
#                     "EvidenceScore": round(
#                         float(point_score or 0),
#                         6,
#                     ),
#                     "EvidenceDate": (
#                         extract_payload_metadata(
#                             payload,
#                             "EvidenceDate",
#                             "evidenceDate",
#                             "evidence_date",
#                             "DocumentDate",
#                             "documentDate",
#                             "document_date",
#                             "CreatedAt",
#                             "createdAt",
#                             "created_at",
#                             "UpdatedAt",
#                             "updatedAt",
#                             "updated_at",
#                             "metadata.EvidenceDate",
#                             "metadata.DocumentDate",
#                             "metadata.CreatedAt",
#                             "metadata.UpdatedAt",
#                         )
#                     ),
#                 }
#             )

#         return normalized_results

#     async def invoke_llm(
#         self,
#         prompt: str,
#     ) -> Any:
#         if hasattr(self.llm, "ainvoke"):
#             return await self.llm.ainvoke(prompt)

#         if hasattr(self.llm, "invoke"):
#             return await asyncio.to_thread(
#                 self.llm.invoke,
#                 prompt,
#             )

#         raise TypeError(
#             "Configured LLM does not support "
#             "invoke() or ainvoke()."
#         )

#     async def log_llm_token_usage(
#         self,
#         usage: Mapping[str, Any],
#         *,
#         bearer_token: str | None,
#         company_id: str,
#         tender_id: str,
#         project_id: str,
#         user_id: str,
#         evidence_summary_id: str,
#         source_ids: list[str],
#         duration: float,
#     ) -> None:
#         """
#         Send one aggregated token-usage log for the complete
#         Evidence Summary Agent run.

#         The bearer token is used only for the token-usage API.
#         It is never written to MongoDB or enterprise logs.
#         """

#         input_tokens = int(
#             usage.get(
#                 "input_tokens",
#                 0,
#             )
#             or 0
#         )

#         output_tokens = int(
#             usage.get(
#                 "output_tokens",
#                 0,
#             )
#             or 0
#         )

#         total_tokens = int(
#             usage.get(
#                 "total_tokens",
#                 input_tokens + output_tokens,
#             )
#             or (
#                 input_tokens
#                 + output_tokens
#             )
#         )

#         model_name = str(
#             usage.get(
#                 "model",
#                 "",
#             )
#             or ""
#         ).strip()

#         payload = {
#             "applicationName": "Evidence Summary",
#             "sourceIds": source_ids,
#             "runId": evidence_summary_id,
#             "userId": user_id,
#             "purpose": "Evidence Summary",
#             "method": "ainvoke",
#             "agentName": "Evidence Summary Agent",
#             "usageType": "LLM",
#             "inputToken": input_tokens,
#             "outputToken": output_tokens,
#             "totalTokens": total_tokens,
#             "model": model_name,
#             "duration": round(
#                 float(duration or 0),
#                 3,
#             ),
#             # TokenUsageService calculates cost using the model
#             # pricing table when value is zero.
#             "cost": {
#                 "currency": "USD",
#                 "value": 0,
#             },
#             "companyId": company_id,
#             "tenderId": tender_id,
#             "projectId": project_id,
#         }

#         print(
#             "Evidence Summary token logging state:",
#             {
#                 "bearerTokenPresent": bool(
#                     bearer_token
#                 ),
#                 "bearerTokenLength": (
#                     len(bearer_token)
#                     if bearer_token
#                     else 0
#                 ),
#                 "companyId": company_id,
#                 "tenderId": tender_id,
#                 "projectId": project_id,
#                 "userId": user_id,
#                 "runId": evidence_summary_id,
#                 "inputToken": input_tokens,
#                 "outputToken": output_tokens,
#                 "totalTokens": total_tokens,
#                 "model": model_name,
#                 "duration": payload[
#                     "duration"
#                 ],
#                 "sourceIdCount": len(
#                     source_ids
#                 ),
#             },
#         )

#         result = await TokenUsageService.log_usage(
#             payload=payload,
#             bearer_token=bearer_token,
#         )

#         if not result.get(
#             "success",
#             False,
#         ):
#             print(
#                 "Evidence Summary token usage "
#                 "logging failed:",
#                 result,
#             )
#             return

#         print(
#             "Evidence Summary token usage "
#             "logged successfully:",
#             {
#                 "runId": evidence_summary_id,
#                 "model": model_name,
#                 "totalTokens": total_tokens,
#             },
#         )

#     async def process_requirement(
#         self,
#         requirement: Mapping[str, Any],
#         *,
#         requirement_number: int,
#         company_id: str,
#         tender_id: str,
#         evidence_summary_id: str,
#         bearer_token: str | None,
#         item_status: str,
#         semaphore: asyncio.Semaphore,
#     ) -> dict[str, Any]:
#         """
#         Generate exactly one evidence-summary item for one Agent 1
#         deduplicated requirement.

#         A result is returned even when Qdrant finds no evidence.
#         """

#         async with semaphore:
#             canonical_requirement = str(
#                 get_first_value(
#                     requirement,
#                     "CanonicalRequirement",
#                     "canonicalRequirement",
#                     "RequirementText",
#                     "requirementText",
#                     default="",
#                 )
#                 or ""
#             ).strip()

#             if not canonical_requirement:
#                 raise ValueError(
#                     "A deduplicated requirement is missing "
#                     "CanonicalRequirement."
#                 )

#             deduplicated_requirement_id = str(
#                 get_first_value(
#                     requirement,
#                     "DeduplicatedRequirementId",
#                     "deduplicatedRequirementId",
#                     default=(
#                         f"DEDUP-{requirement_number:04d}"
#                     ),
#                 )
#             ).strip()

#             requirement_type = str(
#                 get_first_value(
#                     requirement,
#                     "RequirementType",
#                     "requirementType",
#                     "requirement_type",
#                     default="",
#                 )
#                 or ""
#             ).strip()

#             requirement_ids = normalize_string_list(
#                 get_first_value(
#                     requirement,
#                     "RequirementIds",
#                     "requirementIds",
#                     default=[],
#                 )
#             )

#             intent_values = collect_intent_values(
#                 requirement
#             )

#             intent_result = {
#                 "CapabilityIntent": (
#                     intent_values.get(
#                         "CapabilityIntent",
#                         [],
#                     )
#                 ),
#                 "EvidenceSections": (
#                     intent_values.get(
#                         "EvidenceSections",
#                         [],
#                     )
#                 ),
#                 "SemanticAnchors": (
#                     intent_values.get(
#                         "SemanticAnchors",
#                         [],
#                     )
#                 ),
#             }

#             search_query = build_evidence_search_query(
#                 canonical_requirement=(
#                     canonical_requirement
#                 ),
#                 intent_values=intent_values,
#             )

#             qdrant_points = await self.search_qdrant(
#                 company_id=company_id,
#                 search_query=search_query,
#             )

#             evidence_sources = (
#                 self.normalize_qdrant_results(
#                     qdrant_points
#                 )
#             )

#             base_output = {
#                 "EvidenceSummaryItemId": (
#                     f"EVIDENCE-{requirement_number:04d}"
#                 ),
#                 "DeduplicatedRequirementId": (
#                     deduplicated_requirement_id
#                 ),
#                 "RequirementIds": (
#                     requirement_ids
#                 ),
#                 "CanonicalRequirement": (
#                     canonical_requirement
#                 ),
#                 "RequirementType": (
#                     requirement_type
#                 ),
#                 "IntentResult": intent_result,
#                 "EvidenceSources": evidence_sources,
#                 "Status": item_status,
#             }

#             # Every requirement receives an output item. When Qdrant
#             # returns nothing, no LLM call is made.
#             if not evidence_sources:
#                 return {
#                     **base_output,
#                     "EvidenceFound": False,
#                     "EvidenceReason": (
#                         "No relevant company evidence was "
#                         "retrieved from Qdrant."
#                     ),
#                     "EvidenceSummary": "",
#                     "EvidenceConfidence": 0.0,
#                     "MissingEvidenceReason": (
#                         "No company evidence chunks matched "
#                         "the requirement, CompanyId and "
#                         "configured relevance threshold."
#                     ),
#                 }

#             prompt = build_evidence_summary_prompt(
#                 canonical_requirement=(
#                     canonical_requirement
#                 ),
#                 intent_values=intent_values,
#                 evidence_sources=evidence_sources,
#             )

#             llm_start_time = time.perf_counter()

#             llm_response = await self.invoke_llm(
#                 prompt
#             )

#             llm_duration = (
#                 time.perf_counter()
#                 - llm_start_time
#             )

#             parsed_result = parse_llm_json_response(
#                 llm_response
#             )

#             source_ids = [
#                 str(
#                     evidence_source.get(
#                         "EvidenceId",
#                         "",
#                     )
#                 )
#                 for evidence_source in evidence_sources
#                 if str(
#                     evidence_source.get(
#                         "EvidenceId",
#                         "",
#                     )
#                 ).strip()
#             ]

#             llm_usage = (
#                 TokenUsageService.extract_token_usage(
#                     llm_response
#                 )
#             )

#             token_usage_record = {
#                 "input_tokens": int(
#                     llm_usage.get(
#                         "input_tokens",
#                         0,
#                     )
#                     or 0
#                 ),
#                 "output_tokens": int(
#                     llm_usage.get(
#                         "output_tokens",
#                         0,
#                     )
#                     or 0
#                 ),
#                 "total_tokens": int(
#                     llm_usage.get(
#                         "total_tokens",
#                         0,
#                     )
#                     or 0
#                 ),
#                 "model": str(
#                     llm_usage.get(
#                         "model",
#                         "",
#                     )
#                     or ""
#                 ).strip(),
#                 "duration": float(
#                     llm_duration
#                     or 0
#                 ),
#                 "source_ids": source_ids,
#             }

#             confidence_value = (
#                 parsed_result.get(
#                     "EvidenceConfidence",
#                     parsed_result.get(
#                         "Confidence",
#                         0,
#                     ),
#                 )
#             )

#             try:
#                 evidence_confidence = float(
#                     confidence_value or 0
#                 )

#             except (TypeError, ValueError):
#                 evidence_confidence = 0.0

#             evidence_confidence = max(
#                 0.0,
#                 min(
#                     1.0,
#                     evidence_confidence,
#                 ),
#             )

#             evidence_found = normalize_boolean(
#                 parsed_result.get(
#                     "EvidenceFound",
#                     False,
#                 )
#             )

#             evidence_reason = str(
#                 parsed_result.get(
#                     "EvidenceReason",
#                     "",
#                 )
#                 or ""
#             ).strip()

#             evidence_summary = str(
#                 parsed_result.get(
#                     "EvidenceSummary",
#                     "",
#                 )
#                 or ""
#             ).strip()

#             missing_evidence_reason_value = (
#                 parsed_result.get(
#                     "MissingEvidenceReason"
#                 )
#             )

#             missing_evidence_reason = (
#                 str(
#                     missing_evidence_reason_value
#                     or ""
#                 ).strip()
#             )

#             if evidence_found:
#                 missing_evidence_reason = None

#                 if not evidence_reason:
#                     evidence_reason = (
#                         "The retrieved company evidence "
#                         "materially supports the requirement."
#                     )

#             else:
#                 evidence_summary = ""
#                 evidence_confidence = 0.0

#                 if not evidence_reason:
#                     evidence_reason = (
#                         "The retrieved chunks do not provide "
#                         "sufficient support for the requirement."
#                     )

#                 if not missing_evidence_reason:
#                     missing_evidence_reason = (
#                         "The retrieved evidence does not "
#                         "sufficiently demonstrate the required "
#                         "capability, compliance or experience."
#                     )

#             return {
#                 **base_output,
#                 "EvidenceFound": evidence_found,
#                 "EvidenceReason": evidence_reason,
#                 "EvidenceSummary": evidence_summary,
#                 "EvidenceConfidence": round(
#                     evidence_confidence,
#                     4,
#                 ),
#                 "MissingEvidenceReason": (
#                     missing_evidence_reason
#                 ),
#                 # Internal-only usage information. generate() removes
#                 # this field before saving the EvidenceSummary item.
#                 "_TokenUsage": token_usage_record,
#             }

#     def normalize_request_payload(
#         self,
#         input_data: Any,
#     ) -> dict[str, Any]:
#         if hasattr(input_data, "model_dump"):
#             return input_data.model_dump(
#                 mode="python"
#             )

#         if isinstance(input_data, Mapping):
#             return dict(input_data)

#         raise ValueError(
#             "Input must be a Pydantic model or dictionary."
#         )

#     async def generate(
#         self,
#         input_data: Any,
#         *,
#         bearer_token: str | None = None,
#         correlation_id: str | None = None,
#         config: RunnableConfig | None = None,
#     ) -> dict[str, Any]:
#         del config

#         payload = self.normalize_request_payload(
#             input_data
#         )

#         company_id = str(
#             payload.get("CompanyId")
#             or payload.get("companyId")
#             or payload.get("company_id")
#             or ""
#         ).strip()

#         tender_id = str(
#             payload.get("TenderId")
#             or payload.get("tenderId")
#             or payload.get("tender_id")
#             or ""
#         ).strip()

#         is_regenerate = normalize_boolean(
#             payload.get("IsRegenerate")
#             if "IsRegenerate" in payload
#             else (
#                 payload.get("isRegenerate")
#                 if "isRegenerate" in payload
#                 else payload.get("is_regenerate")
#             )
#         )

#         user_id = str(
#             payload.get("UserId")
#             or payload.get("userId")
#             or payload.get("user_id")
#             or ""
#         ).strip()

#         user_name = str(
#             payload.get("UserName")
#             or payload.get("userName")
#             or payload.get("user_name")
#             or ""
#         ).strip()

#         project_id = str(
#             payload.get("ProjectId")
#             or payload.get("projectId")
#             or payload.get("project_id")
#             or ""
#         ).strip()

#         dynamic_bearer_token = (
#             bearer_token
#             or payload.get("Token")
#             or payload.get("token")
#             or payload.get("BearerToken")
#             or payload.get("bearerToken")
#         )

#         final_status = (
#             "IsRegenerated"
#             if is_regenerate
#             else "Active"
#         )

#         if not company_id:
#             raise ValueError("CompanyId is required")

#         if not tender_id:
#             raise ValueError("TenderId is required")

#         source_document = (
#             await self.read_latest_deduplication_document(
#                 company_id=company_id,
#                 tender_id=tender_id,
#             )
#         )

#         deduplicated_requirements = (
#             extract_deduplicated_requirements(
#                 source_document
#             )
#         )

#         deduplication_id = str(
#             source_document.get("_id", "")
#         )

#         created_at = utc_now()

#         destination_document = {
#             "CompanyId": company_id,
#             "TenderId": tender_id,
#             "DeduplicationId": deduplication_id,
#             "IsRegenerate": is_regenerate,
#             "UserId": user_id,
#             "UserName": user_name,
#             "ProjectId": project_id,
#             "Summary": {
#                 "TotalRequirements": len(
#                     deduplicated_requirements
#                 ),
#                 "EvidenceFoundCount": 0,
#                 "NoEvidenceFoundCount": len(
#                     deduplicated_requirements
#                 ),
#                 "TotalEvidenceSummaries": 0,
#             },
#             "Output": {
#                 "EvidenceSummaries": []
#             },
#             "Status": "Processing",
#             "Error": None,
#             "CreatedAt": created_at,
#             "UpdatedAt": created_at,
#             "CompletedAt": None,
#         }


#         insert_result = await asyncio.to_thread(
#             self.destination_collection.insert_one,
#             destination_document,
#         )

#         evidence_summary_object_id = (
#             insert_result.inserted_id
#         )

#         evidence_summary_id = str(
#             evidence_summary_object_id
#         )

#         tracking_token = self._logger.start(
#             message=(
#                 "Evidence summary processing started"
#             ),
#             event_type="EvidenceSummaryStarted",
#             correlation_id=correlation_id,
#         )

#         common_log_payload = {
#             "companyId": company_id,
#             "tenderId": tender_id,
#             "deduplicationId": deduplication_id,
#             "evidenceSummaryId": (
#                 evidence_summary_id
#             ),
#             "inputRequirementCount": len(
#                 deduplicated_requirements
#             ),
#         }

#         await asyncio.to_thread(
#             self._logger.log,
#             message=(
#                 "Evidence summary processing started"
#             ),
#             event_type="EvidenceSummaryStarted",
#             is_success=True,
#             duration_ms=0,
#             start_time=tracking_token[
#                 "start_time"
#             ],
#             end_time=None,
#             payload=common_log_payload,
#             correlation_id=tracking_token[
#                 "correlation_id"
#             ],
#         )

#         try:
#             await self.validate_qdrant_collection()

#             await self.run_qdrant_preflight(
#                 company_id=company_id,
#                 requirements=(
#                     deduplicated_requirements
#                 ),
#             )

#             semaphore = asyncio.Semaphore(
#                 self.max_concurrency
#             )

#             evidence_summary_tasks = [
#                 asyncio.create_task(
#                     self.process_requirement(
#                         requirement=requirement,
#                         requirement_number=(
#                             requirement_index
#                         ),
#                         company_id=company_id,
#                         tender_id=tender_id,
#                         evidence_summary_id=(
#                             evidence_summary_id
#                         ),
#                         bearer_token=(
#                             dynamic_bearer_token
#                         ),
#                         item_status=final_status,
#                         semaphore=semaphore,
#                     )
#                 )
#                 for requirement_index, requirement in enumerate(
#                     deduplicated_requirements,
#                     start=1,
#                 )
#             ]

#             try:
#                 evidence_summaries = (
#                     await asyncio.gather(
#                         *evidence_summary_tasks
#                     )
#                 )

#             except Exception:
#                 for task in evidence_summary_tasks:
#                     if not task.done():
#                         task.cancel()

#                 await asyncio.gather(
#                     *evidence_summary_tasks,
#                     return_exceptions=True,
#                 )

#                 raise

#             # ------------------------------------------------
#             # Aggregate Evidence Summary LLM usage for this run.
#             # One token-usage HTTP request is sent, matching the
#             # run-level logging behaviour used by Agent 1.
#             # ------------------------------------------------

#             token_usage_records: list[
#                 Mapping[str, Any]
#             ] = []

#             for evidence_summary in (
#                 evidence_summaries
#             ):
#                 token_usage_record = (
#                     evidence_summary.pop(
#                         "_TokenUsage",
#                         None,
#                     )
#                 )

#                 if isinstance(
#                     token_usage_record,
#                     Mapping,
#                 ):
#                     token_usage_records.append(
#                         token_usage_record
#                     )

#             if token_usage_records:
#                 total_input_tokens = sum(
#                     int(
#                         record.get(
#                             "input_tokens",
#                             0,
#                         )
#                         or 0
#                     )
#                     for record in (
#                         token_usage_records
#                     )
#                 )

#                 total_output_tokens = sum(
#                     int(
#                         record.get(
#                             "output_tokens",
#                             0,
#                         )
#                         or 0
#                     )
#                     for record in (
#                         token_usage_records
#                     )
#                 )

#                 total_tokens = sum(
#                     int(
#                         record.get(
#                             "total_tokens",
#                             0,
#                         )
#                         or (
#                             int(
#                                 record.get(
#                                     "input_tokens",
#                                     0,
#                                 )
#                                 or 0
#                             )
#                             + int(
#                                 record.get(
#                                     "output_tokens",
#                                     0,
#                                 )
#                                 or 0
#                             )
#                         )
#                     )
#                     for record in (
#                         token_usage_records
#                     )
#                 )

#                 total_llm_duration = sum(
#                     float(
#                         record.get(
#                             "duration",
#                             0,
#                         )
#                         or 0
#                     )
#                     for record in (
#                         token_usage_records
#                     )
#                 )

#                 model_names = [
#                     str(
#                         record.get(
#                             "model",
#                             "",
#                         )
#                         or ""
#                     ).strip()
#                     for record in (
#                         token_usage_records
#                     )
#                     if str(
#                         record.get(
#                             "model",
#                             "",
#                         )
#                         or ""
#                     ).strip()
#                 ]

#                 model_name = (
#                     model_names[0]
#                     if model_names
#                     else str(
#                         os.getenv(
#                             "OPENAI_MODEL",
#                             "",
#                         )
#                         or os.getenv(
#                             "MISTRAL_MODEL",
#                             "",
#                         )
#                         or os.getenv(
#                             "GROQ_MODEL",
#                             "",
#                         )
#                         or ""
#                     ).strip()
#                 )

#                 unique_source_ids: list[str] = []
#                 seen_source_ids: set[str] = set()

#                 for record in token_usage_records:
#                     record_source_ids = (
#                         record.get(
#                             "source_ids",
#                             [],
#                         )
#                     )

#                     if not isinstance(
#                         record_source_ids,
#                         Sequence,
#                     ) or isinstance(
#                         record_source_ids,
#                         (
#                             str,
#                             bytes,
#                             bytearray,
#                         ),
#                     ):
#                         record_source_ids = [
#                             record_source_ids
#                         ]

#                     for source_id_value in (
#                         record_source_ids
#                     ):
#                         source_id = str(
#                             source_id_value
#                             or ""
#                         ).strip()

#                         if (
#                             not source_id
#                             or source_id
#                             in seen_source_ids
#                         ):
#                             continue

#                         seen_source_ids.add(
#                             source_id
#                         )
#                         unique_source_ids.append(
#                             source_id
#                         )

#                 await self.log_llm_token_usage(
#                     usage={
#                         "input_tokens": (
#                             total_input_tokens
#                         ),
#                         "output_tokens": (
#                             total_output_tokens
#                         ),
#                         "total_tokens": (
#                             total_tokens
#                         ),
#                         "model": model_name,
#                     },
#                     bearer_token=(
#                         dynamic_bearer_token
#                     ),
#                     company_id=company_id,
#                     tender_id=tender_id,
#                     project_id=project_id,
#                     user_id=user_id,
#                     evidence_summary_id=(
#                         evidence_summary_id
#                     ),
#                     source_ids=(
#                         unique_source_ids
#                     ),
#                     duration=(
#                         total_llm_duration
#                     ),
#                 )

#             else:
#                 print(
#                     "Evidence Summary token logging "
#                     "skipped: no Evidence Summary LLM "
#                     "call was made."
#                 )

#             evidence_found_count = sum(
#                 1
#                 for evidence_summary in evidence_summaries
#                 if evidence_summary.get(
#                     "EvidenceFound",
#                     False,
#                 )
#             )

#             summary = {
#                 "TotalRequirements": len(
#                     deduplicated_requirements
#                 ),
#                 "EvidenceFoundCount": (
#                     evidence_found_count
#                 ),
#                 "NoEvidenceFoundCount": (
#                     len(evidence_summaries)
#                     - evidence_found_count
#                 ),
#                 "TotalEvidenceSummaries": len(
#                     evidence_summaries
#                 ),
#             }

#             output = {
#                 "EvidenceSummaries": (
#                     evidence_summaries
#                 )
#             }

#             completed_at = utc_now()

#             await asyncio.to_thread(
#                 self.destination_collection.update_one,
#                 {
#                     "_id": evidence_summary_object_id
#                 },
#                 {
#                     "$set": {
#                         "Summary": summary,
#                         "Output": output,
#                         "Status": final_status,
#                         "Error": None,
#                         "UpdatedAt": completed_at,
#                         "CompletedAt": completed_at,
#                     }
#                 },
#             )


#             await asyncio.to_thread(
#                 self._logger.end,
#                 tracking_token=tracking_token,
#                 is_success=True,
#                 message=(
#                     "Evidence summary processing completed"
#                 ),
#                 event_type=(
#                     "EvidenceSummaryCompleted"
#                 ),
#                 payload={
#                     **common_log_payload,
#                     "evidenceFoundCount": (
#                         evidence_found_count
#                     ),
#                     "noEvidenceFoundCount": (
#                         len(evidence_summaries)
#                         - evidence_found_count
#                     ),
#                     "outputRequirementCount": len(
#                         evidence_summaries
#                     ),
#                 },
#             )

#             return {
#                 "EvidenceSummaryId": (
#                     evidence_summary_id
#                 ),
#                 "Status": final_status,
#                 "Result": {
#                     "Summary": summary,
#                     "Output": output,
#                 },
#             }

#         except Exception as exc:
#             print(
#                 "Evidence Summary Agent failed:",
#                 {
#                     "errorType": type(exc).__name__,
#                     "statusCode": getattr(
#                         exc,
#                         "status_code",
#                         None,
#                     ),
#                     "errorCode": getattr(
#                         exc,
#                         "code",
#                         None,
#                     ),
#                     "message": str(exc),
#                 },
#             )

#             failed_at = utc_now()

#             await asyncio.to_thread(
#                 self.destination_collection.update_one,
#                 {
#                     "_id": evidence_summary_object_id
#                 },
#                 {
#                     "$set": {
#                         "Status": "Failed",
#                         "Error": str(exc),
#                         "UpdatedAt": failed_at,
#                         "CompletedAt": failed_at,
#                     }
#                 },
#             )

#             await asyncio.to_thread(
#                 self._logger.end,
#                 tracking_token=tracking_token,
#                 is_success=False,
#                 message=(
#                     "Evidence summary processing failed"
#                 ),
#                 event_type="EvidenceSummaryFailed",
#                 payload={
#                     **common_log_payload,
#                     "error": str(exc),
#                     "errorType": type(exc).__name__,
#                 },
#             )

#             raise

#     async def run(
#         self,
#         input_data: Any,
#         **kwargs: Any,
#     ) -> dict[str, Any]:
#         return await self.generate(
#             input_data=input_data,
#             **kwargs,
#         )

#     async def process(
#         self,
#         input_data: Any,
#         **kwargs: Any,
#     ) -> dict[str, Any]:
#         return await self.generate(
#             input_data=input_data,
#             **kwargs,
#         )

#     async def ainvoke(
#         self,
#         input_data: Any,
#         config: RunnableConfig | None = None,
#         **kwargs: Any,
#     ) -> dict[str, Any]:
#         return await self.generate(
#             input_data=input_data,
#             config=config,
#             **kwargs,
#         )

#     async def get_by_id(
#         self,
#         evidence_summary_id: str,
#     ) -> dict[str, Any] | None:
#         if not ObjectId.is_valid(
#             evidence_summary_id
#         ):
#             return None

#         document = await asyncio.to_thread(
#             self.destination_collection.find_one,
#             {
#                 "_id": ObjectId(
#                     evidence_summary_id
#                 )
#             },
#         )

#         if document is None:
#             return None

#         return serialize_mongo_value(document)


# EvidenceSummaryAgent = RequirementEvidenceSummaryAgent
# Agent = RequirementEvidenceSummaryAgent




from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

from bson import ObjectId
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models

from app.infrastructure.database import get_database
from app.infrastructure.load_llms import (
    create_llm,
    get_openai_api_key,
)
from app.infrastructure.logger import Logging
from app.infrastructure.token_usage import TokenUsageService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_environment_value(
    variable_name: str,
    default: str = "",
) -> str:
    return str(
        os.getenv(variable_name, default)
        or default
    ).strip()


def get_required_environment_value(
    variable_name: str,
) -> str:
    value = get_environment_value(variable_name)

    if not value:
        raise ValueError(
            f"{variable_name} is missing in the .env file"
        )

    return value


def normalize_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, (int, float)):
        return value != 0

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
        }

    return False


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        values: Sequence[Any] = [value]

    elif isinstance(value, Sequence) and not isinstance(
        value,
        (bytes, bytearray),
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

        normalized_item = item_text.casefold()

        if normalized_item in seen:
            continue

        seen.add(normalized_item)
        result.append(item_text)

    return result


def get_first_value(
    source: Any,
    *keys: str,
    default: Any = None,
) -> Any:
    if not isinstance(source, Mapping):
        return default

    for key in keys:
        if key in source:
            value = source.get(key)

            if value is not None:
                return value

    return default


def get_nested_value(
    source: Any,
    dotted_key: str,
) -> Any:
    current_value = source

    for key in dotted_key.split("."):
        if not isinstance(current_value, Mapping):
            return None

        current_value = current_value.get(key)

    return current_value


def serialize_mongo_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Mapping):
        return {
            str(key): serialize_mongo_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            serialize_mongo_value(item)
            for item in value
        ]

    return value


def build_id_values(value: str) -> list[Any]:
    values: list[Any] = [value]

    if ObjectId.is_valid(value):
        values.append(ObjectId(value))

    return values


def build_company_tender_query(
    company_id: str,
    tender_id: str,
) -> dict[str, Any]:
    company_values = build_id_values(company_id)
    tender_values = build_id_values(tender_id)

    return {
        "$and": [
            {
                "$or": [
                    {
                        "CompanyId": {
                            "$in": company_values
                        }
                    },
                    {
                        "companyId": {
                            "$in": company_values
                        }
                    },
                    {
                        "company_id": {
                            "$in": company_values
                        }
                    },
                ]
            },
            {
                "$or": [
                    {
                        "TenderId": {
                            "$in": tender_values
                        }
                    },
                    {
                        "tenderId": {
                            "$in": tender_values
                        }
                    },
                    {
                        "tender_id": {
                            "$in": tender_values
                        }
                    },
                ]
            },
        ]
    }


def extract_deduplicated_requirements(
    source_document: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidate_paths = (
        "Output.DeduplicatedRequirements",
        "Result.DeduplicatedRequirements",
        "Output.Result.DeduplicatedRequirements",
        "DeduplicatedRequirements",
    )

    for path in candidate_paths:
        value = get_nested_value(
            source_document,
            path,
        )

        if isinstance(value, list):
            return [
                dict(item)
                for item in value
                if isinstance(item, Mapping)
            ]

    return []


def get_requirement_is_regenerated(
    requirement: Mapping[str, Any],
) -> bool:
    direct_value = get_first_value(
        requirement,
        "IsRegenerated",
        "isRegenerated",
        "is_regenerated",
        default=None,
    )

    if direct_value is not None:
        return normalize_boolean(direct_value)

    status_value = str(
        get_first_value(
            requirement,
            "Status",
            "status",
            default="",
        )
        or ""
    ).strip()

    if status_value.casefold() == "isregenerating":
        return True

    source_requirements = get_first_value(
        requirement,
        "SourceRequirements",
        "sourceRequirements",
        default=[],
    )

    if not isinstance(source_requirements, list):
        return False

    return any(
        normalize_boolean(
            get_first_value(
                source_requirement,
                "IsRegenerated",
                "isRegenerated",
                "is_regenerated",
                default=False,
            )
        )
        for source_requirement in source_requirements
        if isinstance(source_requirement, Mapping)
    )


def build_generation_fields(
    requirement: Mapping[str, Any],
) -> dict[str, Any]:
    is_regenerated = (
        get_requirement_is_regenerated(
            requirement
        )
    )

    return {
        "IsGenerated": True,
        "IsRegenerated": is_regenerated,
        "Status": (
            "IsRegenerating"
            if is_regenerated
            else "Active"
        ),
    }


def collect_intent_values(
    requirement: Mapping[str, Any],
) -> dict[str, list[str]]:
    """
    Read the evidence-routing metadata produced by Agent 1.

    Preferred Agent 1 output fields:

        CapabilityIntent
        EvidenceSections
        SemanticAnchors

    IntentResult and SourceRequirements are retained as fallback
    sources for backward compatibility.
    """

    capability_intents: list[str] = []
    evidence_sections: list[str] = []
    semantic_anchors: list[str] = []

    # Preferred direct Agent 1 output.
    capability_intents.extend(
        normalize_string_list(
            get_first_value(
                requirement,
                "CapabilityIntent",
                "capability_intent",
                "capabilityIntent",
                default=[],
            )
        )
    )

    evidence_sections.extend(
        normalize_string_list(
            get_first_value(
                requirement,
                "EvidenceSections",
                "evidence_sections",
                "evidenceSections",
                default=[],
            )
        )
    )

    semantic_anchors.extend(
        normalize_string_list(
            get_first_value(
                requirement,
                "SemanticAnchors",
                "semantic_anchors",
                "semanticAnchors",
                default=[],
            )
        )
    )

    intent_sources: list[Mapping[str, Any]] = []

    direct_intent = get_first_value(
        requirement,
        "IntentResult",
        "intentResult",
        "intent_result",
        default=None,
    )

    if isinstance(direct_intent, Mapping):
        intent_sources.append(direct_intent)

    source_requirements = get_first_value(
        requirement,
        "SourceRequirements",
        "sourceRequirements",
        default=[],
    )

    if isinstance(source_requirements, list):
        for source_requirement in source_requirements:
            if not isinstance(
                source_requirement,
                Mapping,
            ):
                continue

            # Direct fields on the original requirement.
            capability_intents.extend(
                normalize_string_list(
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
                normalize_string_list(
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
                normalize_string_list(
                    get_first_value(
                        source_requirement,
                        "SemanticAnchors",
                        "semantic_anchors",
                        "semanticAnchors",
                        default=[],
                    )
                )
            )

            source_intent = get_first_value(
                source_requirement,
                "IntentResult",
                "intentResult",
                "intent_result",
                default=None,
            )

            if isinstance(source_intent, Mapping):
                intent_sources.append(source_intent)

    for intent_source in intent_sources:
        capability_intents.extend(
            normalize_string_list(
                get_first_value(
                    intent_source,
                    "CapabilityIntent",
                    "capability_intent",
                    "capabilityIntent",
                    default=[],
                )
            )
        )

        evidence_sections.extend(
            normalize_string_list(
                get_first_value(
                    intent_source,
                    "EvidenceSections",
                    "evidence_sections",
                    "evidenceSections",
                    default=[],
                )
            )
        )

        semantic_anchors.extend(
            normalize_string_list(
                get_first_value(
                    intent_source,
                    "SemanticAnchors",
                    "semantic_anchors",
                    "semanticAnchors",
                    default=[],
                )
            )
        )

    return {
        "CapabilityIntent": normalize_string_list(
            capability_intents
        ),
        "EvidenceSections": normalize_string_list(
            evidence_sections
        ),
        "SemanticAnchors": normalize_string_list(
            semantic_anchors
        ),
    }


def build_evidence_search_query(
    canonical_requirement: str,
    intent_values: Mapping[str, Any],
) -> str:
    """
    Build the semantic-search query sent to Qdrant.

    SemanticAnchors are placed first because they are the primary
    evidence-retrieval terms produced by Agent 1. The requirement and
    routing context are retained to disambiguate short anchors.
    """

    capability_intents = normalize_string_list(
        intent_values.get("CapabilityIntent")
    )

    evidence_sections = normalize_string_list(
        intent_values.get("EvidenceSections")
    )

    semantic_anchors = normalize_string_list(
        intent_values.get("SemanticAnchors")
    )

    query_parts: list[str] = []

    if semantic_anchors:
        query_parts.append(
            "Primary semantic anchors: "
            + ", ".join(semantic_anchors)
        )

    query_parts.append(
        f"Tender requirement: {canonical_requirement}"
    )

    if capability_intents:
        query_parts.append(
            "Capability intent: "
            + ", ".join(capability_intents)
        )

    if evidence_sections:
        query_parts.append(
            "Expected evidence sections: "
            + ", ".join(evidence_sections)
        )

    search_query = "\n".join(query_parts)

    print(
        "Evidence search terms prepared:",
        {
            "SemanticAnchors": semantic_anchors,
            "CapabilityIntent": capability_intents,
            "EvidenceSections": evidence_sections,
            "queryLength": len(search_query),
        },
    )

    return search_query


def extract_payload_text(
    payload: Mapping[str, Any],
) -> str:
    text_paths = (
        "ChunkText",
        "chunkText",
        "chunk_text",
        "Text",
        "text",
        "Content",
        "content",
        "page_content",
        "PageContent",
        "document",
        "Document",
        "metadata.ChunkText",
        "metadata.chunkText",
        "metadata.chunk_text",
        "metadata.Text",
        "metadata.text",
        "metadata.Content",
        "metadata.content",
        "metadata.page_content",
    )

    for path in text_paths:
        value = get_nested_value(payload, path)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def extract_payload_metadata(
    payload: Mapping[str, Any],
    *paths: str,
) -> str:
    for path in paths:
        value = get_nested_value(payload, path)

        if value is None:
            continue

        value_text = str(value).strip()

        if value_text:
            return value_text

    return ""


def parse_llm_json_response(response: Any) -> dict[str, Any]:
    content = getattr(response, "content", response)

    if isinstance(content, list):
        content_parts: list[str] = []

        for item in content:
            if isinstance(item, Mapping):
                item_text = (
                    item.get("text")
                    or item.get("content")
                    or ""
                )
            else:
                item_text = str(item)

            if str(item_text).strip():
                content_parts.append(
                    str(item_text).strip()
                )

        content_text = "\n".join(content_parts)

    else:
        content_text = str(content or "").strip()

    if not content_text:
        raise ValueError(
            "The LLM returned an empty evidence-summary response."
        )

    cleaned_text = content_text.strip()

    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`").strip()

        if cleaned_text.lower().startswith("json"):
            cleaned_text = cleaned_text[4:].strip()

    first_brace = cleaned_text.find("{")
    last_brace = cleaned_text.rfind("}")

    if first_brace >= 0 and last_brace > first_brace:
        cleaned_text = cleaned_text[
            first_brace:last_brace + 1
        ]

    try:
        parsed = json.loads(cleaned_text)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "The LLM evidence-summary response was not valid JSON. "
            f"Response: {content_text[:1000]}"
        ) from exc

    if not isinstance(parsed, Mapping):
        raise ValueError(
            "The LLM evidence-summary response must be a JSON object."
        )

    return dict(parsed)


def build_evidence_summary_prompt(
    canonical_requirement: str,
    intent_values: Mapping[str, Any],
    evidence_sources: list[dict[str, Any]],
) -> str:
    """
    Build the LLM prompt for one deduplicated requirement.

    The LLM receives only the selected Qdrant evidence chunks and
    returns the compact evidence decision fields required by MongoDB.
    """

    evidence_blocks: list[str] = []

    for evidence_index, evidence_source in enumerate(
        evidence_sources,
        start=1,
    ):
        evidence_blocks.append(
            "\n".join(
                [
                    f"[Evidence {evidence_index}]",
                    (
                        "EvidenceId: "
                        f"{evidence_source.get('EvidenceId', '')}"
                    ),
                    (
                        "ChunkId: "
                        f"{evidence_source.get('ChunkId', '')}"
                    ),
                    (
                        "SourceTitle: "
                        f"{evidence_source.get('SourceTitle', '')}"
                    ),
                    (
                        "SourceDocument: "
                        f"{evidence_source.get('SourceDocument', '')}"
                    ),
                    (
                        "DocumentType: "
                        f"{evidence_source.get('DocumentType', '')}"
                    ),
                    (
                        "RelatedSection: "
                        f"{evidence_source.get('RelatedSection', '')}"
                    ),
                    (
                        "EvidenceScore: "
                        f"{evidence_source.get('EvidenceScore', 0)}"
                    ),
                    "EvidenceText:",
                    str(
                        evidence_source.get(
                            "EvidenceText",
                            "",
                        )
                    ),
                ]
            )
        )

    evidence_text = "\n\n".join(
        evidence_blocks
    )

    return f"""
You are the Evidence Summary Agent for a tender-response system.

Evaluate whether the retrieved company evidence supports the tender requirement.

STRICT RULES:
1. Use only the supplied evidence chunks.
2. Do not invent clients, projects, certifications, figures, dates, technologies, outcomes or capabilities.
3. EvidenceFound must be true only when the supplied chunks materially support the requirement.
4. EvidenceReason must briefly explain why the evidence supports or does not support the requirement.
5. EvidenceSummary must be concise and grounded only in the supplied evidence.
6. MissingEvidenceReason must be null when EvidenceFound is true.
7. When EvidenceFound is false, EvidenceSummary must be an empty string and MissingEvidenceReason must clearly state what evidence is missing.
8. EvidenceConfidence must be a number between 0 and 1.
9. Return valid JSON only. Do not return markdown or code fences.

TENDER REQUIREMENT:
{canonical_requirement}

CAPABILITY INTENT:
{json.dumps(intent_values.get('CapabilityIntent', []), ensure_ascii=False)}

EXPECTED EVIDENCE SECTIONS:
{json.dumps(intent_values.get('EvidenceSections', []), ensure_ascii=False)}

SEMANTIC ANCHORS:
{json.dumps(intent_values.get('SemanticAnchors', []), ensure_ascii=False)}

RETRIEVED COMPANY EVIDENCE:
{evidence_text}

Return exactly this JSON structure:
{{
  "EvidenceFound": true,
  "EvidenceReason": "Why the supplied evidence does or does not support the requirement.",
  "EvidenceSummary": "Concise evidence summary grounded only in the supplied chunks.",
  "EvidenceConfidence": 0.0,
  "MissingEvidenceReason": null
}}
""".strip()


class RequirementEvidenceSummaryAgent:
    """
    Evidence Summary Agent.

    Complete flow contained in this one file:

    1. Read the latest successfully regenerated Requirement
       Deduplication result from MongoDB.
    2. Extract Output.DeduplicatedRequirements[].
    3. Search company-specific evidence chunks in Qdrant.
    4. Send each requirement and its retrieved chunks to the LLM.
    5. Save the Evidence Summary output in MongoDB.
    """

    def __init__(
        self,
        llm: Any | None = None,
        embeddings: Any | None = None,
        qdrant_client: QdrantClient | None = None,
    ) -> None:
        self._llm = llm
        self._embeddings = embeddings
        self._qdrant_client = qdrant_client
        self._resolved_qdrant_url: str | None = None
        self._resolved_qdrant_vector_name: str | None = None
        self._resolved_qdrant_vector_size: int | None = None

        self._logger = Logging(
            agent_name="Evidence Summary Agent",
            source_module=(
                "app.agents."
                "Evidence_Summary_Agent.Agent"
            ),
        )

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = create_llm()

        return self._llm

    @property
    def embeddings(self) -> Any:
        if self._embeddings is None:
            embedding_model = get_environment_value(
                "EMBEDDING_MODEL",
                "text-embedding-3-small",
            )

            self._embeddings = OpenAIEmbeddings(
                model=embedding_model,
                api_key=get_openai_api_key(),
            )

        return self._embeddings

    @staticmethod
    def normalize_qdrant_url(
        value: str,
    ) -> str:
        """
        Normalize a Qdrant server base URL.

        Correct example:

            http://localhost:6333

        Do not include /dashboard or /collections.
        """

        normalized_url = str(
            value or ""
        ).strip().rstrip("/")

        removable_suffixes = (
            "/dashboard",
            "/collections",
        )

        for suffix in removable_suffixes:
            if normalized_url.lower().endswith(
                suffix
            ):
                normalized_url = normalized_url[
                    :-len(suffix)
                ].rstrip("/")
                break

        return normalized_url

    def get_qdrant_candidate_urls(
        self,
    ) -> list[str]:
        """
        Build the ordered list of Qdrant URLs to try.

        QDRANT_URL is tried first.

        QDRANT_FALLBACK_URL is tried second and defaults to:

            http://localhost:6333
        """

        configured_url = (
            get_required_environment_value(
                "QDRANT_URL"
            )
        )

        fallback_url = get_environment_value(
            "QDRANT_FALLBACK_URL",
            "http://localhost:6333",
        )

        candidate_urls: list[str] = []

        for raw_url in (
            configured_url,
            fallback_url,
        ):
            normalized_url = (
                self.normalize_qdrant_url(
                    raw_url
                )
            )

            if not normalized_url:
                continue

            if normalized_url in candidate_urls:
                continue

            candidate_urls.append(
                normalized_url
            )

        return candidate_urls

    def create_qdrant_client(
        self,
        *,
        qdrant_url: str,
        qdrant_api_key: str,
        qdrant_timeout: float,
    ) -> QdrantClient:
        """
        Create a Qdrant client.

        check_compatibility=False suppresses the version warning.
        Older qdrant-client versions are supported through fallback.
        """

        client_arguments: dict[str, Any] = {
            "url": qdrant_url,
            "api_key": (
                qdrant_api_key
                if qdrant_api_key
                else None
            ),
            "timeout": qdrant_timeout,
        }

        try:
            return QdrantClient(
                **client_arguments,
                check_compatibility=False,
            )

        except TypeError:
            return QdrantClient(
                **client_arguments
            )

    @staticmethod
    def get_qdrant_vector_size(
        vector_parameters: Any,
    ) -> int | None:
        """
        Read the vector size from either a Qdrant model or a plain
        dictionary.
        """

        if vector_parameters is None:
            return None

        if isinstance(vector_parameters, Mapping):
            raw_size = vector_parameters.get("size")

        else:
            raw_size = getattr(
                vector_parameters,
                "size",
                None,
            )

        if raw_size is None:
            return None

        try:
            return int(raw_size)

        except (TypeError, ValueError):
            return None

    def resolve_qdrant_vector_configuration(
        self,
        collection_info: Any,
    ) -> tuple[str | None, int | None]:
        """
        Resolve whether CPDocuments uses an unnamed dense vector or
        one or more named dense vectors.

        QDRANT_VECTOR_NAME is used when explicitly configured.
        When the collection has exactly one named dense vector, that
        name is selected automatically.
        """

        collection_config = getattr(
            collection_info,
            "config",
            None,
        )

        collection_params = getattr(
            collection_config,
            "params",
            None,
        )

        vectors_config = getattr(
            collection_params,
            "vectors",
            None,
        )

        # Fallback for responses represented as dictionaries.
        if vectors_config is None:
            if hasattr(collection_info, "model_dump"):
                try:
                    collection_data = (
                        collection_info.model_dump()
                    )
                except Exception:
                    collection_data = {}

            elif isinstance(collection_info, Mapping):
                collection_data = dict(
                    collection_info
                )

            else:
                collection_data = {}

            vectors_config = (
                collection_data
                .get("config", {})
                .get("params", {})
                .get("vectors")
            )

        configured_vector_name = (
            get_environment_value(
                "QDRANT_VECTOR_NAME"
            )
        )

        # A dictionary means this collection uses named vectors.
        if isinstance(vectors_config, Mapping):
            available_vector_names = [
                str(vector_name)
                for vector_name in vectors_config.keys()
                if str(vector_name).strip()
            ]

            if not available_vector_names:
                raise RuntimeError(
                    "Qdrant collection does not contain a dense "
                    "vector configuration. Available named dense "
                    "vectors are empty."
                )

            if configured_vector_name:
                if (
                    configured_vector_name
                    not in available_vector_names
                ):
                    raise RuntimeError(
                        "Configured QDRANT_VECTOR_NAME does not "
                        "exist in the Qdrant collection. "
                        f"Configured: "
                        f"'{configured_vector_name}'. "
                        f"Available: "
                        f"{available_vector_names}."
                    )

                selected_vector_name = (
                    configured_vector_name
                )

            elif len(available_vector_names) == 1:
                selected_vector_name = (
                    available_vector_names[0]
                )

            else:
                preferred_names = (
                    "default",
                    "text",
                    "content",
                    "embedding",
                    "dense",
                    "vector",
                )

                selected_vector_name = next(
                    (
                        preferred_name
                        for preferred_name
                        in preferred_names
                        if preferred_name
                        in available_vector_names
                    ),
                    None,
                )

                if selected_vector_name is None:
                    raise RuntimeError(
                        "Qdrant collection contains multiple named "
                        "vectors and no unambiguous vector can be "
                        "selected. Set QDRANT_VECTOR_NAME in .env. "
                        f"Available vector names: "
                        f"{available_vector_names}."
                    )

            selected_parameters = vectors_config[
                selected_vector_name
            ]

            selected_vector_size = (
                self.get_qdrant_vector_size(
                    selected_parameters
                )
            )

            return (
                selected_vector_name,
                selected_vector_size,
            )

        # A single VectorParams object means the collection uses the
        # unnamed/default dense vector.
        selected_vector_size = (
            self.get_qdrant_vector_size(
                vectors_config
            )
        )

        if configured_vector_name:
            raise RuntimeError(
                "QDRANT_VECTOR_NAME is configured as "
                f"'{configured_vector_name}', but the collection "
                "uses an unnamed/default dense vector. Remove "
                "QDRANT_VECTOR_NAME from .env."
            )

        if vectors_config is None:
            raise RuntimeError(
                "Unable to read the dense-vector configuration "
                "from the Qdrant collection."
            )

        return (
            None,
            selected_vector_size,
        )

    @property
    def qdrant_client(self) -> QdrantClient:
        """
        Resolve and cache a working Qdrant client.

        A URL is accepted only when the configured collection exists.
        This prevents frontend URLs such as localhost:5173 from being
        treated as Qdrant servers.
        """

        if self._qdrant_client is not None:
            return self._qdrant_client

        qdrant_api_key = get_environment_value(
            "QDRANT_API_KEY"
        )

        qdrant_timeout = float(
            get_environment_value(
                "QDRANT_TIMEOUT",
                "60",
            )
        )

        candidate_urls = (
            self.get_qdrant_candidate_urls()
        )

        attempt_errors: list[
            dict[str, Any]
        ] = []

        for candidate_url in candidate_urls:
            candidate_client: (
                QdrantClient | None
            ) = None

            print(
                "Testing Qdrant configuration:",
                {
                    "url": candidate_url,
                    "collection": (
                        self.qdrant_collection_name
                    ),
                    "apiKeyPresent": bool(
                        qdrant_api_key
                    ),
                    "timeoutSeconds": (
                        qdrant_timeout
                    ),
                },
            )

            try:
                candidate_client = (
                    self.create_qdrant_client(
                        qdrant_url=candidate_url,
                        qdrant_api_key=(
                            qdrant_api_key
                        ),
                        qdrant_timeout=(
                            qdrant_timeout
                        ),
                    )
                )

                collection_info = (
                    candidate_client.get_collection(
                        collection_name=(
                            self.qdrant_collection_name
                        )
                    )
                )

                (
                    resolved_vector_name,
                    resolved_vector_size,
                ) = (
                    self.resolve_qdrant_vector_configuration(
                        collection_info
                    )
                )

                self._qdrant_client = (
                    candidate_client
                )

                self._resolved_qdrant_url = (
                    candidate_url
                )

                self._resolved_qdrant_vector_name = (
                    resolved_vector_name
                )

                self._resolved_qdrant_vector_size = (
                    resolved_vector_size
                )

                print(
                    "Qdrant server selected:",
                    {
                        "url": candidate_url,
                        "collection": (
                            self.qdrant_collection_name
                        ),
                        "status": str(
                            getattr(
                                collection_info,
                                "status",
                                "available",
                            )
                        ),
                        "vectorName": (
                            resolved_vector_name
                            if resolved_vector_name
                            else "<unnamed>"
                        ),
                        "vectorSize": (
                            resolved_vector_size
                        ),
                    },
                )

                return self._qdrant_client

            except Exception as exc:
                status_code = getattr(
                    exc,
                    "status_code",
                    None,
                )

                attempt_error = {
                    "url": candidate_url,
                    "errorType": (
                        type(exc).__name__
                    ),
                    "statusCode": status_code,
                    "message": str(exc),
                }

                attempt_errors.append(
                    attempt_error
                )

                print(
                    "Qdrant candidate rejected:",
                    attempt_error,
                )

                if candidate_client is not None:
                    try:
                        candidate_client.close()
                    except Exception:
                        pass

        attempted_urls = ", ".join(
            candidate_urls
        )

        raise RuntimeError(
            "Unable to connect to a Qdrant server "
            f"containing collection "
            f"'{self.qdrant_collection_name}'. "
            f"Attempted URLs: {attempted_urls}. "
            "Set QDRANT_URL or QDRANT_FALLBACK_URL "
            "to the Qdrant REST base URL, normally "
            "http://localhost:6333. "
            f"Attempt details: {attempt_errors}"
        )

    @property
    def database(self) -> Any:
        return get_database()

    @property
    def source_collection(self) -> Any:
        collection_name = get_environment_value(
            "DEDUPLICATION_COLLECTION_NAME",
            "TenderRequirementDeduplications",
        )

        return self.database[collection_name]

    @property
    def destination_collection(self) -> Any:
        collection_name = get_environment_value(
            "EVIDENCE_SUMMARY_COLLECTION_NAME",
            "TenderEvidenceSummaries",
        )

        return self.database[collection_name]

    @property
    def qdrant_collection_name(self) -> str:
        return get_environment_value(
            "QDRANT_COLLECTION_NAME",
            "CPDocuments",
        )

    @property
    def top_k(self) -> int:
        return max(
            1,
            int(
                get_environment_value(
                    "EVIDENCE_TOP_K",
                    "5",
                )
            ),
        )

    @property
    def score_threshold(self) -> float:
        return float(
            get_environment_value(
                "EVIDENCE_SCORE_THRESHOLD",
                "0.55",
            )
        )

    @property
    def max_concurrency(self) -> int:
        return max(
            1,
            int(
                get_environment_value(
                    "EVIDENCE_MAX_CONCURRENCY",
                    "3",
                )
            ),
        )

    @property
    def chunk_character_limit(self) -> int:
        return max(
            500,
            int(
                get_environment_value(
                    "EVIDENCE_CHUNK_CHARACTER_LIMIT",
                    "4000",
                )
            ),
        )

    @property
    def total_context_character_limit(self) -> int:
        return max(
            self.chunk_character_limit,
            int(
                get_environment_value(
                    "EVIDENCE_TOTAL_CONTEXT_CHARACTER_LIMIT",
                    "16000",
                )
            ),
        )

    async def read_latest_deduplication_document(
        self,
        company_id: str,
        tender_id: str,
    ) -> dict[str, Any]:
        query = build_company_tender_query(
            company_id=company_id,
            tender_id=tender_id,
        )

        query["$and"].append(
            {
                "Status": "IsRegenerated"
            }
        )

        print(
            "Evidence source database:",
            self.source_collection.database.name,
        )

        print(
            "Evidence source collection:",
            self.source_collection.name,
        )

        print(
            "Evidence source query:",
            query,
        )

        source_document = await asyncio.to_thread(
            self.source_collection.find_one,
            query,
            sort=[
                ("CompletedAt", -1),
                ("_id", -1),
            ],
        )

        if source_document is None:
            raise ValueError(
                "No IsRegenerated deduplication document was found "
                "for the supplied CompanyId and TenderId. "
                f"CompanyId: {company_id}. "
                f"TenderId: {tender_id}."
            )

        deduplicated_requirements = (
            extract_deduplicated_requirements(
                source_document
            )
        )

        if not deduplicated_requirements:
            raise ValueError(
                "The IsRegenerated deduplication document does not "
                "contain Output.DeduplicatedRequirements[]."
            )

        print(
            "Deduplicated requirements found:",
            len(deduplicated_requirements),
        )

        return source_document

    def build_qdrant_company_filter(
        self,
        company_id: str,
    ) -> models.Filter:
        company_field_paths = (
            "CompanyId",
            "companyId",
            "company_id",
            "metadata.CompanyId",
            "metadata.companyId",
            "metadata.company_id",
        )

        return models.Filter(
            should=[
                models.FieldCondition(
                    key=field_path,
                    match=models.MatchValue(
                        value=company_id
                    ),
                )
                for field_path in company_field_paths
            ]
        )

    async def validate_qdrant_collection(
        self,
    ) -> None:
        """
        Validate the selected Qdrant connection and collection once
        before starting concurrent requirement processing.
        """

        def validate() -> None:
            try:
                collection_info = (
                    self.qdrant_client.get_collection(
                        collection_name=(
                            self.qdrant_collection_name
                        )
                    )
                )

            except Exception as exc:
                status_code = getattr(
                    exc,
                    "status_code",
                    None,
                )

                raise RuntimeError(
                    "Qdrant collection validation failed. "
                    f"URL: "
                    f"{self._resolved_qdrant_url or 'unresolved'}. "
                    f"Collection: "
                    f"{self.qdrant_collection_name}. "
                    f"Status code: {status_code}. "
                    f"Message: {exc}"
                ) from exc

            print(
                "Qdrant collection validated:",
                {
                    "url": (
                        self._resolved_qdrant_url
                    ),
                    "collection": (
                        self.qdrant_collection_name
                    ),
                    "status": str(
                        getattr(
                            collection_info,
                            "status",
                            "available",
                        )
                    ),
                    "vectorName": (
                        self._resolved_qdrant_vector_name
                        if self._resolved_qdrant_vector_name
                        else "<unnamed>"
                    ),
                    "vectorSize": (
                        self._resolved_qdrant_vector_size
                    ),
                },
            )

        await asyncio.to_thread(validate)

    async def create_query_embedding(
        self,
        search_query: str,
    ) -> list[float]:
        try:
            embedding = await asyncio.to_thread(
                self.embeddings.embed_query,
                search_query,
            )

            print(
                "Embedding generated successfully:",
                {
                    "dimension": len(
                        embedding
                    ),
                    "queryLength": len(
                        search_query
                    ),
                },
            )

            expected_vector_size = (
                self._resolved_qdrant_vector_size
            )

            if (
                expected_vector_size is not None
                and len(embedding)
                != expected_vector_size
            ):
                raise RuntimeError(
                    "Embedding dimension does not match the "
                    "Qdrant collection vector dimension. "
                    f"Embedding dimension: {len(embedding)}. "
                    f"Qdrant dimension: "
                    f"{expected_vector_size}. "
                    "Use the same embedding model that was used "
                    "when CPDocuments was populated."
                )

            return embedding

        except Exception as exc:
            print(
                "Embedding generation failed:",
                {
                    "errorType": type(exc).__name__,
                    "statusCode": getattr(
                        exc,
                        "status_code",
                        None,
                    ),
                    "errorCode": getattr(
                        exc,
                        "code",
                        None,
                    ),
                    "message": str(exc),
                },
            )

            raise

    async def search_qdrant(
        self,
        company_id: str,
        search_query: str,
    ) -> list[Any]:
        query_vector = await self.create_query_embedding(
            search_query
        )

        company_filter = (
            self.build_qdrant_company_filter(
                company_id
            )
        )

        # The name was resolved from the live collection during
        # validation. None means the collection uses the unnamed
        # default vector.
        vector_name = (
            self._resolved_qdrant_vector_name
        )

        def execute_search() -> list[Any]:
            client = self.qdrant_client

            def execute_legacy_search() -> list[Any]:
                if not hasattr(client, "search"):
                    raise TypeError(
                        "The installed qdrant-client does not "
                        "provide search()."
                    )

                search_arguments: dict[str, Any] = {
                    "collection_name": (
                        self.qdrant_collection_name
                    ),
                    "query_vector": query_vector,
                    "query_filter": company_filter,
                    "limit": self.top_k,
                    "with_payload": True,
                }

                if self.score_threshold > 0:
                    search_arguments[
                        "score_threshold"
                    ] = self.score_threshold

                if vector_name:
                    search_arguments[
                        "query_vector"
                    ] = (
                        vector_name,
                        query_vector,
                    )

                return list(
                    client.search(
                        **search_arguments
                    )
                    or []
                )

            if hasattr(client, "query_points"):
                query_arguments: dict[str, Any] = {
                    "collection_name": (
                        self.qdrant_collection_name
                    ),
                    "query": query_vector,
                    "query_filter": company_filter,
                    "limit": self.top_k,
                    "with_payload": True,
                }

                if self.score_threshold > 0:
                    query_arguments[
                        "score_threshold"
                    ] = self.score_threshold

                if vector_name:
                    query_arguments["using"] = (
                        vector_name
                    )

                try:
                    query_response = (
                        client.query_points(
                            **query_arguments
                        )
                    )

                    points = getattr(
                        query_response,
                        "points",
                        query_response,
                    )

                    return list(points or [])

                except Exception as query_exc:
                    query_status_code = getattr(
                        query_exc,
                        "status_code",
                        None,
                    )

                    query_error_message = str(
                        query_exc
                    )

                    query_endpoint_missing = (
                        query_status_code == 404
                        or "404" in query_error_message
                    )

                    if (
                        query_endpoint_missing
                        and hasattr(client, "search")
                    ):
                        print(
                            "Qdrant query_points endpoint "
                            "returned 404. Falling back "
                            "to search()."
                        )

                        return execute_legacy_search()

                    raise

            if hasattr(client, "search"):
                return execute_legacy_search()

            raise TypeError(
                "The installed qdrant-client does not support "
                "query_points() or search()."
            )

        try:
            print(
                "Starting Qdrant search:",
                {
                    "collection": (
                        self.qdrant_collection_name
                    ),
                    "topK": self.top_k,
                    "scoreThreshold": (
                        self.score_threshold
                    ),
                    "companyId": company_id,
                    "vectorName": (
                        vector_name
                        if vector_name
                        else "<unnamed>"
                    ),
                    "vectorSize": len(
                        query_vector
                    ),
                },
            )

            results = await asyncio.to_thread(
                execute_search
            )

            print(
                "Qdrant search completed:",
                {
                    "resultCount": len(results),
                },
            )

            return results

        except Exception as exc:
            print(
                "Qdrant search failed:",
                {
                    "errorType": type(exc).__name__,
                    "statusCode": getattr(
                        exc,
                        "status_code",
                        None,
                    ),
                    "message": str(exc),
                },
            )

            raise RuntimeError(
                "Qdrant search failed. "
                f"Error type: "
                f"{type(exc).__name__}. "
                f"Message: {exc}"
            ) from exc

    async def run_qdrant_preflight(
        self,
        *,
        company_id: str,
        requirements: list[dict[str, Any]],
    ) -> None:
        """
        Execute one real embedding and Qdrant search before creating
        all evidence tasks.

        This catches vector-name, vector-dimension, endpoint and
        filter errors once, instead of repeating them for every
        requirement.
        """

        if not requirements:
            raise ValueError(
                "Qdrant preflight cannot run because no "
                "deduplicated requirements were supplied."
            )

        first_requirement = requirements[0]

        canonical_requirement = str(
            get_first_value(
                first_requirement,
                "CanonicalRequirement",
                "canonicalRequirement",
                "RequirementText",
                "requirementText",
                default="",
            )
            or ""
        ).strip()

        if not canonical_requirement:
            raise ValueError(
                "The first deduplicated requirement is missing "
                "CanonicalRequirement."
            )

        intent_values = collect_intent_values(
            first_requirement
        )

        search_query = build_evidence_search_query(
            canonical_requirement=canonical_requirement,
            intent_values=intent_values,
        )

        await self.search_qdrant(
            company_id=company_id,
            search_query=search_query,
        )

        print(
            "Qdrant preflight completed successfully:",
            {
                "url": self._resolved_qdrant_url,
                "collection": (
                    self.qdrant_collection_name
                ),
                "vectorName": (
                    self._resolved_qdrant_vector_name
                    if self._resolved_qdrant_vector_name
                    else "<unnamed>"
                ),
                "vectorSize": (
                    self._resolved_qdrant_vector_size
                ),
            },
        )

    def normalize_qdrant_results(
        self,
        points: list[Any],
    ) -> list[dict[str, Any]]:
        """
        Convert raw Qdrant points into the compact evidence-source
        structure stored in MongoDB and supplied to the LLM.
        """

        normalized_results: list[
            dict[str, Any]
        ] = []

        total_characters = 0

        for point in points:
            payload = getattr(
                point,
                "payload",
                {},
            ) or {}

            if not isinstance(payload, Mapping):
                payload = {}

            evidence_text = extract_payload_text(
                payload
            )

            if not evidence_text:
                continue

            remaining_characters = (
                self.total_context_character_limit
                - total_characters
            )

            if remaining_characters <= 0:
                break

            allowed_characters = min(
                self.chunk_character_limit,
                remaining_characters,
            )

            evidence_text = evidence_text[
                :allowed_characters
            ]

            total_characters += len(
                evidence_text
            )

            point_id = getattr(
                point,
                "id",
                "",
            )

            point_score = getattr(
                point,
                "score",
                0,
            )

            document_id = extract_payload_metadata(
                payload,
                "DocumentId",
                "documentId",
                "document_id",
                "metadata.DocumentId",
                "metadata.documentId",
                "metadata.document_id",
            )

            source_title = extract_payload_metadata(
                payload,
                "SourceTitle",
                "sourceTitle",
                "source_title",
                "Title",
                "title",
                "DocumentTitle",
                "documentTitle",
                "Heading",
                "heading",
                "metadata.SourceTitle",
                "metadata.sourceTitle",
                "metadata.title",
                "metadata.Heading",
                "metadata.heading",
            )

            source_document = extract_payload_metadata(
                payload,
                "SourceDocument",
                "sourceDocument",
                "source_document",
                "DocumentName",
                "documentName",
                "FileName",
                "fileName",
                "file_name",
                "SourceFileName",
                "sourceFileName",
                "metadata.SourceDocument",
                "metadata.DocumentName",
                "metadata.FileName",
                "metadata.fileName",
                "metadata.file_name",
                "metadata.source",
            )

            if not source_document:
                source_document = document_id

            normalized_results.append(
                {
                    "EvidenceId": str(
                        point_id
                    ),
                    "ChunkId": extract_payload_metadata(
                        payload,
                        "ChunkId",
                        "chunkId",
                        "chunk_id",
                        "metadata.ChunkId",
                        "metadata.chunkId",
                        "metadata.chunk_id",
                    ),
                    "SourceTitle": source_title,
                    "SourceDocument": (
                        source_document
                    ),
                    "DocumentType": (
                        extract_payload_metadata(
                            payload,
                            "DocumentType",
                            "documentType",
                            "document_type",
                            "FileType",
                            "fileType",
                            "file_type",
                            "Type",
                            "type",
                            "metadata.DocumentType",
                            "metadata.documentType",
                            "metadata.FileType",
                            "metadata.type",
                        )
                    ),
                    "RelatedSection": (
                        extract_payload_metadata(
                            payload,
                            "RelatedSection",
                            "relatedSection",
                            "related_section",
                            "Section",
                            "section",
                            "SectionName",
                            "sectionName",
                            "Heading",
                            "heading",
                            "metadata.RelatedSection",
                            "metadata.Section",
                            "metadata.section",
                            "metadata.SectionName",
                            "metadata.sectionName",
                            "metadata.Heading",
                            "metadata.heading",
                        )
                    ),
                    "EvidenceText": evidence_text,
                    "EvidenceScore": round(
                        float(point_score or 0),
                        6,
                    ),
                    "EvidenceDate": (
                        extract_payload_metadata(
                            payload,
                            "EvidenceDate",
                            "evidenceDate",
                            "evidence_date",
                            "DocumentDate",
                            "documentDate",
                            "document_date",
                            "CreatedAt",
                            "createdAt",
                            "created_at",
                            "UpdatedAt",
                            "updatedAt",
                            "updated_at",
                            "metadata.EvidenceDate",
                            "metadata.DocumentDate",
                            "metadata.CreatedAt",
                            "metadata.UpdatedAt",
                        )
                    ),
                }
            )

        return normalized_results

    async def invoke_llm(
        self,
        prompt: str,
    ) -> Any:
        if hasattr(self.llm, "ainvoke"):
            return await self.llm.ainvoke(prompt)

        if hasattr(self.llm, "invoke"):
            return await asyncio.to_thread(
                self.llm.invoke,
                prompt,
            )

        raise TypeError(
            "Configured LLM does not support "
            "invoke() or ainvoke()."
        )

    async def log_llm_token_usage(
        self,
        usage: Mapping[str, Any],
        *,
        bearer_token: str | None,
        company_id: str,
        tender_id: str,
        project_id: str,
        user_id: str,
        evidence_summary_id: str,
        source_ids: list[str],
        duration: float,
    ) -> None:
        """
        Send one aggregated token-usage log for the complete
        Evidence Summary Agent run.

        The bearer token is used only for the token-usage API.
        It is never written to MongoDB or enterprise logs.
        """

        input_tokens = int(
            usage.get(
                "input_tokens",
                0,
            )
            or 0
        )

        output_tokens = int(
            usage.get(
                "output_tokens",
                0,
            )
            or 0
        )

        total_tokens = int(
            usage.get(
                "total_tokens",
                input_tokens + output_tokens,
            )
            or (
                input_tokens
                + output_tokens
            )
        )

        model_name = str(
            usage.get(
                "model",
                "",
            )
            or ""
        ).strip()

        payload = {
            "applicationName": "Evidence Summary",
            "sourceIds": source_ids,
            "runId": evidence_summary_id,
            "userId": user_id,
            "purpose": "Evidence Summary",
            "method": "ainvoke",
            "agentName": "Evidence Summary Agent",
            "usageType": "LLM",
            "inputToken": input_tokens,
            "outputToken": output_tokens,
            "totalTokens": total_tokens,
            "model": model_name,
            "duration": round(
                float(duration or 0),
                3,
            ),
            # TokenUsageService calculates cost using the model
            # pricing table when value is zero.
            "cost": {
                "currency": "USD",
                "value": 0,
            },
            "companyId": company_id,
            "tenderId": tender_id,
            "projectId": project_id,
        }

        print(
            "Evidence Summary token logging state:",
            {
                "bearerTokenPresent": bool(
                    bearer_token
                ),
                "bearerTokenLength": (
                    len(bearer_token)
                    if bearer_token
                    else 0
                ),
                "companyId": company_id,
                "tenderId": tender_id,
                "projectId": project_id,
                "userId": user_id,
                "runId": evidence_summary_id,
                "inputToken": input_tokens,
                "outputToken": output_tokens,
                "totalTokens": total_tokens,
                "model": model_name,
                "duration": payload[
                    "duration"
                ],
                "sourceIdCount": len(
                    source_ids
                ),
            },
        )

        result = await TokenUsageService.log_usage(
            payload=payload,
            bearer_token=bearer_token,
        )

        if not result.get(
            "success",
            False,
        ):
            print(
                "Evidence Summary token usage "
                "logging failed:",
                result,
            )
            return

        print(
            "Evidence Summary token usage "
            "logged successfully:",
            {
                "runId": evidence_summary_id,
                "model": model_name,
                "totalTokens": total_tokens,
            },
        )

    async def process_requirement(
        self,
        requirement: Mapping[str, Any],
        *,
        requirement_number: int,
        company_id: str,
        tender_id: str,
        evidence_summary_id: str,
        bearer_token: str | None,
        item_status: str,
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        """
        Generate exactly one evidence-summary item for one Agent 1
        deduplicated requirement.

        A result is returned even when Qdrant finds no evidence.
        """

        async with semaphore:
            canonical_requirement = str(
                get_first_value(
                    requirement,
                    "CanonicalRequirement",
                    "canonicalRequirement",
                    "RequirementText",
                    "requirementText",
                    default="",
                )
                or ""
            ).strip()

            if not canonical_requirement:
                raise ValueError(
                    "A deduplicated requirement is missing "
                    "CanonicalRequirement."
                )

            deduplicated_requirement_id = str(
                get_first_value(
                    requirement,
                    "DeduplicatedRequirementId",
                    "deduplicatedRequirementId",
                    default=(
                        f"DEDUP-{requirement_number:04d}"
                    ),
                )
            ).strip()

            requirement_type = str(
                get_first_value(
                    requirement,
                    "RequirementType",
                    "requirementType",
                    "requirement_type",
                    default="",
                )
                or ""
            ).strip()

            requirement_ids = normalize_string_list(
                get_first_value(
                    requirement,
                    "RequirementIds",
                    "requirementIds",
                    default=[],
                )
            )

            intent_values = collect_intent_values(
                requirement
            )

            intent_result = {
                "CapabilityIntent": (
                    intent_values.get(
                        "CapabilityIntent",
                        [],
                    )
                ),
                "EvidenceSections": (
                    intent_values.get(
                        "EvidenceSections",
                        [],
                    )
                ),
                "SemanticAnchors": (
                    intent_values.get(
                        "SemanticAnchors",
                        [],
                    )
                ),
            }

            search_query = build_evidence_search_query(
                canonical_requirement=(
                    canonical_requirement
                ),
                intent_values=intent_values,
            )

            qdrant_points = await self.search_qdrant(
                company_id=company_id,
                search_query=search_query,
            )

            evidence_sources = (
                self.normalize_qdrant_results(
                    qdrant_points
                )
            )

            base_output = {
                "EvidenceSummaryItemId": (
                    f"EVIDENCE-{requirement_number:04d}"
                ),
                "DeduplicatedRequirementId": (
                    deduplicated_requirement_id
                ),
                "RequirementIds": (
                    requirement_ids
                ),
                "CanonicalRequirement": (
                    canonical_requirement
                ),
                "RequirementType": (
                    requirement_type
                ),
                "IntentResult": intent_result,
                "EvidenceSources": evidence_sources,
                "Status": item_status,
            }

            # Every requirement receives an output item. When Qdrant
            # returns nothing, no LLM call is made.
            if not evidence_sources:
                return {
                    **base_output,
                    "EvidenceFound": False,
                    "EvidenceReason": (
                        "No relevant company evidence was "
                        "retrieved from Qdrant."
                    ),
                    "EvidenceSummary": "",
                    "EvidenceConfidence": 0.0,
                    "MissingEvidenceReason": (
                        "No company evidence chunks matched "
                        "the requirement, CompanyId and "
                        "configured relevance threshold."
                    ),
                }

            prompt = build_evidence_summary_prompt(
                canonical_requirement=(
                    canonical_requirement
                ),
                intent_values=intent_values,
                evidence_sources=evidence_sources,
            )

            llm_start_time = time.perf_counter()

            llm_response = await self.invoke_llm(
                prompt
            )

            llm_duration = (
                time.perf_counter()
                - llm_start_time
            )

            parsed_result = parse_llm_json_response(
                llm_response
            )

            source_ids = [
                str(
                    evidence_source.get(
                        "EvidenceId",
                        "",
                    )
                )
                for evidence_source in evidence_sources
                if str(
                    evidence_source.get(
                        "EvidenceId",
                        "",
                    )
                ).strip()
            ]

            llm_usage = (
                TokenUsageService.extract_token_usage(
                    llm_response
                )
            )

            token_usage_record = {
                "input_tokens": int(
                    llm_usage.get(
                        "input_tokens",
                        0,
                    )
                    or 0
                ),
                "output_tokens": int(
                    llm_usage.get(
                        "output_tokens",
                        0,
                    )
                    or 0
                ),
                "total_tokens": int(
                    llm_usage.get(
                        "total_tokens",
                        0,
                    )
                    or 0
                ),
                "model": str(
                    llm_usage.get(
                        "model",
                        "",
                    )
                    or ""
                ).strip(),
                "duration": float(
                    llm_duration
                    or 0
                ),
                "source_ids": source_ids,
            }

            confidence_value = (
                parsed_result.get(
                    "EvidenceConfidence",
                    parsed_result.get(
                        "Confidence",
                        0,
                    ),
                )
            )

            try:
                evidence_confidence = float(
                    confidence_value or 0
                )

            except (TypeError, ValueError):
                evidence_confidence = 0.0

            evidence_confidence = max(
                0.0,
                min(
                    1.0,
                    evidence_confidence,
                ),
            )

            evidence_found = normalize_boolean(
                parsed_result.get(
                    "EvidenceFound",
                    False,
                )
            )

            evidence_reason = str(
                parsed_result.get(
                    "EvidenceReason",
                    "",
                )
                or ""
            ).strip()

            evidence_summary = str(
                parsed_result.get(
                    "EvidenceSummary",
                    "",
                )
                or ""
            ).strip()

            missing_evidence_reason_value = (
                parsed_result.get(
                    "MissingEvidenceReason"
                )
            )

            missing_evidence_reason = (
                str(
                    missing_evidence_reason_value
                    or ""
                ).strip()
            )

            if evidence_found:
                missing_evidence_reason = None

                if not evidence_reason:
                    evidence_reason = (
                        "The retrieved company evidence "
                        "materially supports the requirement."
                    )

            else:
                evidence_summary = ""
                evidence_confidence = 0.0

                if not evidence_reason:
                    evidence_reason = (
                        "The retrieved chunks do not provide "
                        "sufficient support for the requirement."
                    )

                if not missing_evidence_reason:
                    missing_evidence_reason = (
                        "The retrieved evidence does not "
                        "sufficiently demonstrate the required "
                        "capability, compliance or experience."
                    )

            return {
                **base_output,
                "EvidenceFound": evidence_found,
                "EvidenceReason": evidence_reason,
                "EvidenceSummary": evidence_summary,
                "EvidenceConfidence": round(
                    evidence_confidence,
                    4,
                ),
                "MissingEvidenceReason": (
                    missing_evidence_reason
                ),
                # Internal-only usage information. generate() removes
                # this field before saving the EvidenceSummary item.
                "_TokenUsage": token_usage_record,
            }

    def normalize_request_payload(
        self,
        input_data: Any,
    ) -> dict[str, Any]:
        if hasattr(input_data, "model_dump"):
            return input_data.model_dump(
                mode="python"
            )

        if isinstance(input_data, Mapping):
            return dict(input_data)

        raise ValueError(
            "Input must be a Pydantic model or dictionary."
        )

    async def generate(
        self,
        input_data: Any,
        *,
        bearer_token: str | None = None,
        correlation_id: str | None = None,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        del config

        payload = self.normalize_request_payload(
            input_data
        )

        company_id = str(
            payload.get("CompanyId")
            or payload.get("companyId")
            or payload.get("company_id")
            or ""
        ).strip()

        tender_id = str(
            payload.get("TenderId")
            or payload.get("tenderId")
            or payload.get("tender_id")
            or ""
        ).strip()

        is_regenerate = normalize_boolean(
            payload.get("IsRegenerate")
            if "IsRegenerate" in payload
            else (
                payload.get("isRegenerate")
                if "isRegenerate" in payload
                else payload.get("is_regenerate")
            )
        )

        user_id = str(
            payload.get("UserId")
            or payload.get("userId")
            or payload.get("user_id")
            or ""
        ).strip()

        user_name = str(
            payload.get("UserName")
            or payload.get("userName")
            or payload.get("user_name")
            or ""
        ).strip()

        project_id = str(
            payload.get("ProjectId")
            or payload.get("projectId")
            or payload.get("project_id")
            or ""
        ).strip()

        dynamic_bearer_token = (
            bearer_token
            or payload.get("Token")
            or payload.get("token")
            or payload.get("BearerToken")
            or payload.get("bearerToken")
        )

        final_status = (
            "IsRegenerated"
            if is_regenerate
            else "Active"
        )

        if not company_id:
            raise ValueError("CompanyId is required")

        if not tender_id:
            raise ValueError("TenderId is required")

        source_document = (
            await self.read_latest_deduplication_document(
                company_id=company_id,
                tender_id=tender_id,
            )
        )

        deduplicated_requirements = (
            extract_deduplicated_requirements(
                source_document
            )
        )

        deduplication_id = str(
            source_document.get("_id", "")
        )

        created_at = utc_now()

        destination_document = {
            "CompanyId": company_id,
            "TenderId": tender_id,
            "DeduplicationId": deduplication_id,
            "IsRegenerate": is_regenerate,
            "UserId": user_id,
            "UserName": user_name,
            "ProjectId": project_id,
            "Summary": {
                "TotalRequirements": len(
                    deduplicated_requirements
                ),
                "EvidenceFoundCount": 0,
                "NoEvidenceFoundCount": len(
                    deduplicated_requirements
                ),
                "TotalEvidenceSummaries": 0,
            },
            "Output": {
                "EvidenceSummaries": []
            },
            "Status": "Processing",
            "Error": None,
            "CreatedAt": created_at,
            "UpdatedAt": created_at,
            "CompletedAt": None,
        }


        insert_result = await asyncio.to_thread(
            self.destination_collection.insert_one,
            destination_document,
        )

        evidence_summary_object_id = (
            insert_result.inserted_id
        )

        evidence_summary_id = str(
            evidence_summary_object_id
        )

        tracking_token = self._logger.start(
            message=(
                "Evidence summary processing started"
            ),
            event_type="EvidenceSummaryStarted",
            correlation_id=correlation_id,
        )

        common_log_payload = {
            "companyId": company_id,
            "tenderId": tender_id,
            "deduplicationId": deduplication_id,
            "evidenceSummaryId": (
                evidence_summary_id
            ),
            "inputRequirementCount": len(
                deduplicated_requirements
            ),
        }

        await asyncio.to_thread(
            self._logger.log,
            message=(
                "Evidence summary processing started"
            ),
            event_type="EvidenceSummaryStarted",
            is_success=True,
            duration_ms=0,
            start_time=tracking_token[
                "start_time"
            ],
            end_time=None,
            payload=common_log_payload,
            correlation_id=tracking_token[
                "correlation_id"
            ],
        )

        try:
            await self.validate_qdrant_collection()

            await self.run_qdrant_preflight(
                company_id=company_id,
                requirements=(
                    deduplicated_requirements
                ),
            )

            semaphore = asyncio.Semaphore(
                self.max_concurrency
            )

            evidence_summary_tasks = [
                asyncio.create_task(
                    self.process_requirement(
                        requirement=requirement,
                        requirement_number=(
                            requirement_index
                        ),
                        company_id=company_id,
                        tender_id=tender_id,
                        evidence_summary_id=(
                            evidence_summary_id
                        ),
                        bearer_token=(
                            dynamic_bearer_token
                        ),
                        item_status=final_status,
                        semaphore=semaphore,
                    )
                )
                for requirement_index, requirement in enumerate(
                    deduplicated_requirements,
                    start=1,
                )
            ]

            try:
                evidence_summaries = (
                    await asyncio.gather(
                        *evidence_summary_tasks
                    )
                )

            except Exception:
                for task in evidence_summary_tasks:
                    if not task.done():
                        task.cancel()

                await asyncio.gather(
                    *evidence_summary_tasks,
                    return_exceptions=True,
                )

                raise

            # ------------------------------------------------
            # Aggregate Evidence Summary LLM usage for this run.
            # One token-usage HTTP request is sent, matching the
            # run-level logging behaviour used by Agent 1.
            # ------------------------------------------------

            token_usage_records: list[
                Mapping[str, Any]
            ] = []

            for evidence_summary in (
                evidence_summaries
            ):
                token_usage_record = (
                    evidence_summary.pop(
                        "_TokenUsage",
                        None,
                    )
                )

                if isinstance(
                    token_usage_record,
                    Mapping,
                ):
                    token_usage_records.append(
                        token_usage_record
                    )

            if token_usage_records:
                total_input_tokens = sum(
                    int(
                        record.get(
                            "input_tokens",
                            0,
                        )
                        or 0
                    )
                    for record in (
                        token_usage_records
                    )
                )

                total_output_tokens = sum(
                    int(
                        record.get(
                            "output_tokens",
                            0,
                        )
                        or 0
                    )
                    for record in (
                        token_usage_records
                    )
                )

                total_tokens = sum(
                    int(
                        record.get(
                            "total_tokens",
                            0,
                        )
                        or (
                            int(
                                record.get(
                                    "input_tokens",
                                    0,
                                )
                                or 0
                            )
                            + int(
                                record.get(
                                    "output_tokens",
                                    0,
                                )
                                or 0
                            )
                        )
                    )
                    for record in (
                        token_usage_records
                    )
                )

                total_llm_duration = sum(
                    float(
                        record.get(
                            "duration",
                            0,
                        )
                        or 0
                    )
                    for record in (
                        token_usage_records
                    )
                )

                model_names = [
                    str(
                        record.get(
                            "model",
                            "",
                        )
                        or ""
                    ).strip()
                    for record in (
                        token_usage_records
                    )
                    if str(
                        record.get(
                            "model",
                            "",
                        )
                        or ""
                    ).strip()
                ]

                model_name = (
                    model_names[0]
                    if model_names
                    else str(
                        os.getenv(
                            "OPENAI_MODEL",
                            "",
                        )
                        or os.getenv(
                            "MISTRAL_MODEL",
                            "",
                        )
                        or os.getenv(
                            "GROQ_MODEL",
                            "",
                        )
                        or ""
                    ).strip()
                )

                unique_source_ids: list[str] = []
                seen_source_ids: set[str] = set()

                for record in token_usage_records:
                    record_source_ids = (
                        record.get(
                            "source_ids",
                            [],
                        )
                    )

                    if not isinstance(
                        record_source_ids,
                        Sequence,
                    ) or isinstance(
                        record_source_ids,
                        (
                            str,
                            bytes,
                            bytearray,
                        ),
                    ):
                        record_source_ids = [
                            record_source_ids
                        ]

                    for source_id_value in (
                        record_source_ids
                    ):
                        source_id = str(
                            source_id_value
                            or ""
                        ).strip()

                        if (
                            not source_id
                            or source_id
                            in seen_source_ids
                        ):
                            continue

                        seen_source_ids.add(
                            source_id
                        )
                        unique_source_ids.append(
                            source_id
                        )

                await self.log_llm_token_usage(
                    usage={
                        "input_tokens": (
                            total_input_tokens
                        ),
                        "output_tokens": (
                            total_output_tokens
                        ),
                        "total_tokens": (
                            total_tokens
                        ),
                        "model": model_name,
                    },
                    bearer_token=(
                        dynamic_bearer_token
                    ),
                    company_id=company_id,
                    tender_id=tender_id,
                    project_id=project_id,
                    user_id=user_id,
                    evidence_summary_id=(
                        evidence_summary_id
                    ),
                    source_ids=(
                        unique_source_ids
                    ),
                    duration=(
                        total_llm_duration
                    ),
                )

            else:
                # No Qdrant evidence means the Evidence Summary LLM
                # was not called. Still create one run-level usage
                # record with zero tokens so the Evidence Agent run
                # remains visible in the central token log.
                await self.log_llm_token_usage(
                    usage={
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "model": (
                            TokenUsageService
                            .resolve_configured_model_name()
                        ),
                    },
                    bearer_token=(
                        dynamic_bearer_token
                    ),
                    company_id=company_id,
                    tender_id=tender_id,
                    project_id=project_id,
                    user_id=user_id,
                    evidence_summary_id=(
                        evidence_summary_id
                    ),
                    source_ids=[],
                    duration=0.0,
                )

                print(
                    "Evidence Summary zero-token run "
                    "logged because no Evidence Summary "
                    "LLM call was required."
                )

            evidence_found_count = sum(
                1
                for evidence_summary in evidence_summaries
                if evidence_summary.get(
                    "EvidenceFound",
                    False,
                )
            )

            summary = {
                "TotalRequirements": len(
                    deduplicated_requirements
                ),
                "EvidenceFoundCount": (
                    evidence_found_count
                ),
                "NoEvidenceFoundCount": (
                    len(evidence_summaries)
                    - evidence_found_count
                ),
                "TotalEvidenceSummaries": len(
                    evidence_summaries
                ),
            }

            output = {
                "EvidenceSummaries": (
                    evidence_summaries
                )
            }

            completed_at = utc_now()

            await asyncio.to_thread(
                self.destination_collection.update_one,
                {
                    "_id": evidence_summary_object_id
                },
                {
                    "$set": {
                        "Summary": summary,
                        "Output": output,
                        "Status": final_status,
                        "Error": None,
                        "UpdatedAt": completed_at,
                        "CompletedAt": completed_at,
                    }
                },
            )


            await asyncio.to_thread(
                self._logger.end,
                tracking_token=tracking_token,
                is_success=True,
                message=(
                    "Evidence summary processing completed"
                ),
                event_type=(
                    "EvidenceSummaryCompleted"
                ),
                payload={
                    **common_log_payload,
                    "evidenceFoundCount": (
                        evidence_found_count
                    ),
                    "noEvidenceFoundCount": (
                        len(evidence_summaries)
                        - evidence_found_count
                    ),
                    "outputRequirementCount": len(
                        evidence_summaries
                    ),
                },
            )

            return {
                "EvidenceSummaryId": (
                    evidence_summary_id
                ),
                "Status": final_status,
                "Result": {
                    "Summary": summary,
                    "Output": output,
                },
            }

        except Exception as exc:
            print(
                "Evidence Summary Agent failed:",
                {
                    "errorType": type(exc).__name__,
                    "statusCode": getattr(
                        exc,
                        "status_code",
                        None,
                    ),
                    "errorCode": getattr(
                        exc,
                        "code",
                        None,
                    ),
                    "message": str(exc),
                },
            )

            failed_at = utc_now()

            await asyncio.to_thread(
                self.destination_collection.update_one,
                {
                    "_id": evidence_summary_object_id
                },
                {
                    "$set": {
                        "Status": "Failed",
                        "Error": str(exc),
                        "UpdatedAt": failed_at,
                        "CompletedAt": failed_at,
                    }
                },
            )

            await asyncio.to_thread(
                self._logger.end,
                tracking_token=tracking_token,
                is_success=False,
                message=(
                    "Evidence summary processing failed"
                ),
                event_type="EvidenceSummaryFailed",
                payload={
                    **common_log_payload,
                    "error": str(exc),
                    "errorType": type(exc).__name__,
                },
            )

            raise

    async def run(
        self,
        input_data: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.generate(
            input_data=input_data,
            **kwargs,
        )

    async def process(
        self,
        input_data: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.generate(
            input_data=input_data,
            **kwargs,
        )

    async def ainvoke(
        self,
        input_data: Any,
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return await self.generate(
            input_data=input_data,
            config=config,
            **kwargs,
        )

    async def get_by_id(
        self,
        evidence_summary_id: str,
    ) -> dict[str, Any] | None:
        if not ObjectId.is_valid(
            evidence_summary_id
        ):
            return None

        document = await asyncio.to_thread(
            self.destination_collection.find_one,
            {
                "_id": ObjectId(
                    evidence_summary_id
                )
            },
        )

        if document is None:
            return None

        return serialize_mongo_value(document)


EvidenceSummaryAgent = RequirementEvidenceSummaryAgent
Agent = RequirementEvidenceSummaryAgent