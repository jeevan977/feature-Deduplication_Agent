
# from __future__ import annotations

# import asyncio
# import json
# from datetime import datetime, timezone
# from typing import Any, Mapping, Sequence

# from bson import ObjectId
# from pymongo.collection import Collection

# from app.agents.Deduplication_Agent.Agent import (
#     RequirementDeduplicationAgent,
# )
# from app.infrastructure.database import (
#     get_deduplication_collection,
#     get_requirement_extraction_collection,
# )


# def utc_now() -> datetime:
#     return datetime.now(timezone.utc)


# def serialize_mongo_value(value: Any) -> Any:
#     """
#     Convert MongoDB values into JSON-safe values
#     for the GET API response.
#     """

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


# def is_list_value(value: Any) -> bool:
#     return isinstance(
#         value,
#         Sequence,
#     ) and not isinstance(
#         value,
#         (
#             str,
#             bytes,
#             bytearray,
#         ),
#     )


# def normalize_key(value: Any) -> str:
#     return (
#         str(value)
#         .replace("_", "")
#         .replace("-", "")
#         .replace(" ", "")
#         .lower()
#     )


# def extract_requirements_from_document(
#     document: Any,
# ) -> list[Any]:
#     """
#     Find requirements in common MongoDB structures.

#     Supported fields include:

#     RawRequirements
#     Requirements
#     ExtractedRequirements
#     Output.Requirements
#     Result.Requirements
#     """

#     requirement_keys = {
#         "rawrequirements",
#         "requirements",
#         "extractedrequirements",
#         "detectedrequirements",
#         "tenderrequirements",
#         "finalrequirements",
#         "requirementitems",
#     }

#     extracted_requirements: list[Any] = []

#     def walk(value: Any) -> None:
#         if isinstance(value, Mapping):
#             for key, child_value in value.items():
#                 normalized_key = normalize_key(key)

#                 if normalized_key in requirement_keys:
#                     if is_list_value(child_value):
#                         for requirement in child_value:
#                             if requirement is not None:
#                                 extracted_requirements.append(
#                                     requirement
#                                 )

#                     elif child_value is not None:
#                         extracted_requirements.append(
#                             child_value
#                         )

#                 else:
#                     walk(child_value)

#         elif is_list_value(value):
#             for child_value in value:
#                 walk(child_value)

#     walk(document)

#     return extracted_requirements


# def requirement_identity(
#     requirement: Any,
# ) -> str:
#     """
#     Remove only exact duplicate input objects.

#     Similar requirements must remain because the
#     LLM is responsible for semantic deduplication.
#     """

#     if isinstance(requirement, Mapping):
#         for key in (
#             "RequirementId",
#             "requirement_id",
#             "Id",
#             "id",
#             "_id",
#         ):
#             requirement_id = requirement.get(key)

#             if requirement_id is not None:
#                 requirement_id_text = str(
#                     requirement_id
#                 ).strip()

#                 if requirement_id_text:
#                     return f"id:{requirement_id_text}"

#     return json.dumps(
#         requirement,
#         ensure_ascii=False,
#         sort_keys=True,
#         default=str,
#     )


# def remove_exact_duplicates(
#     requirements: list[Any],
# ) -> list[Any]:
#     result: list[Any] = []
#     identities: set[str] = set()

#     for requirement in requirements:
#         identity = requirement_identity(
#             requirement
#         )

#         if identity in identities:
#             continue

#         identities.add(identity)
#         result.append(requirement)

#     return result


# def prepare_document_for_copy(
#     source_document: Mapping[str, Any],
# ) -> dict[str, Any]:
#     """
#     Prepare a source document for copying into the
#     deduplication destination document.

#     The source _id is renamed because the destination
#     record has its own _id.
#     """

#     copied_document = dict(source_document)

#     source_id = copied_document.pop(
#         "_id",
#         None,
#     )

#     return {
#         "SourceMongoId": (
#             str(source_id)
#             if source_id is not None
#             else None
#         ),
#         "Document": copied_document,
#     }


# class RequirementDeduplicationService:
#     def __init__(
#         self,
#         source_collection: Collection | None = None,
#         destination_collection: Collection | None = None,
#         agent: RequirementDeduplicationAgent | None = None,
#     ) -> None:
#         self._source_collection = source_collection
#         self._destination_collection = (
#             destination_collection
#         )
#         self._agent = agent

#     @property
#     def source_collection(self) -> Collection:
#         """
#         Input/source collection:

#         TenderRequirementExtractions
#         """

#         if self._source_collection is None:
#             self._source_collection = (
#                 get_requirement_extraction_collection()
#             )

#         return self._source_collection

#     @property
#     def destination_collection(self) -> Collection:
#         """
#         Output/destination collection:

#         TenderRequirementDeduplications
#         """

#         if self._destination_collection is None:
#             self._destination_collection = (
#                 get_deduplication_collection()
#             )

#         return self._destination_collection

#     @property
#     def collection(self) -> Collection:
#         """
#         Compatibility property for existing code.
#         """

#         return self.destination_collection

#     @property
#     def agent(self) -> RequirementDeduplicationAgent:
#         if self._agent is None:
#             self._agent = (
#                 RequirementDeduplicationAgent()
#             )

#         return self._agent

#     def build_source_query(
#         self,
#         company_id: str,
#         tender_id: str,
#     ) -> dict[str, Any]:
#         """
#         Supports both string IDs and Mongo ObjectIds,
#         along with common field-name variations.
#         """

#         company_values: list[Any] = [
#             company_id
#         ]

#         tender_values: list[Any] = [
#             tender_id
#         ]

#         if ObjectId.is_valid(company_id):
#             company_values.append(
#                 ObjectId(company_id)
#             )

#         if ObjectId.is_valid(tender_id):
#             tender_values.append(
#                 ObjectId(tender_id)
#             )

#         return {
#             "$and": [
#                 {
#                     "$or": [
#                         {
#                             "CompanyId": {
#                                 "$in": company_values
#                             }
#                         },
#                         {
#                             "companyId": {
#                                 "$in": company_values
#                             }
#                         },
#                         {
#                             "company_id": {
#                                 "$in": company_values
#                             }
#                         },
#                     ]
#                 },
#                 {
#                     "$or": [
#                         {
#                             "TenderId": {
#                                 "$in": tender_values
#                             }
#                         },
#                         {
#                             "tenderId": {
#                                 "$in": tender_values
#                             }
#                         },
#                         {
#                             "tender_id": {
#                                 "$in": tender_values
#                             }
#                         },
#                     ]
#                 },
#             ]
#         }

#     async def read_source_documents(
#         self,
#         company_id: str,
#         tender_id: str,
#     ) -> list[dict[str, Any]]:
#         """
#         Read input documents from
#         TenderRequirementExtractions.
#         """

#         query = self.build_source_query(
#             company_id=company_id,
#             tender_id=tender_id,
#         )

#         print(
#             "Source database:",
#             self.source_collection.database.name,
#         )

#         print(
#             "Source collection:",
#             self.source_collection.name,
#         )

#         print(
#             "Source query:",
#             query,
#         )

#         def read_documents() -> list[
#             dict[str, Any]
#         ]:
#             return list(
#                 self.source_collection
#                 .find(query)
#                 .sort("_id", -1)
#             )

#         source_documents = await asyncio.to_thread(
#             read_documents
#         )

#         print(
#             "Source documents found:",
#             len(source_documents),
#         )

#         if not source_documents:
#             raise ValueError(
#                 "No source documents were found for "
#                 "the supplied CompanyId and TenderId. "
#                 f"Database: "
#                 f"{self.source_collection.database.name}. "
#                 f"Collection: "
#                 f"{self.source_collection.name}. "
#                 f"CompanyId: {company_id}. "
#                 f"TenderId: {tender_id}."
#             )

#         return source_documents

#     async def process(
#         self,
#         request: Any,
#         bearer_token: str | None = None,
#     ) -> dict[str, Any]:
#         """
#         Main method called by deduplication_route.py.

#         Flow:

#         1. Read CompanyId and TenderId.
#         2. Read source Mongo documents.
#         3. Extract RawRequirements.
#         4. Insert processing record in destination.
#         5. Send requirements to the LLM.
#         6. Save LLM output in destination.
#         """

#         if hasattr(request, "model_dump"):
#             payload = request.model_dump(
#                 mode="python"
#             )

#         elif isinstance(request, Mapping):
#             payload = dict(request)

#         else:
#             raise ValueError(
#                 "Request must be a Pydantic model "
#                 "or dictionary"
#             )

#         company_id = str(
#             payload.get(
#                 "CompanyId",
#                 "",
#             )
#         ).strip()

#         tender_id = str(
#             payload.get(
#                 "TenderId",
#                 "",
#             )
#         ).strip()

#         if not company_id:
#             raise ValueError(
#                 "CompanyId is required"
#             )

#         if not tender_id:
#             raise ValueError(
#                 "TenderId is required"
#             )

#         # ----------------------------------------------
#         # Read source Mongo documents
#         # ----------------------------------------------

#         source_documents = (
#             await self.read_source_documents(
#                 company_id=company_id,
#                 tender_id=tender_id,
#             )
#         )

#         raw_requirements: list[Any] = []
#         source_document_ids: list[str] = []
#         copied_source_documents: list[
#             dict[str, Any]
#         ] = []

#         for source_document in source_documents:
#             source_id = source_document.get(
#                 "_id"
#             )

#             if source_id is not None:
#                 source_document_ids.append(
#                     str(source_id)
#                 )

#             copied_source_documents.append(
#                 prepare_document_for_copy(
#                     source_document
#                 )
#             )

#             requirements = (
#                 extract_requirements_from_document(
#                     source_document
#                 )
#             )

#             raw_requirements.extend(
#                 requirements
#             )

#         raw_requirements = remove_exact_duplicates(
#             raw_requirements
#         )

#         if not raw_requirements:
#             raise ValueError(
#                 "Source documents were found, but "
#                 "no requirements were found. "
#                 "Expected RawRequirements, Requirements, "
#                 "ExtractedRequirements or "
#                 "Output.Requirements."
#             )

#         created_at = utc_now()

#         destination_document = {
#             "CompanyId": company_id,
#             "TenderId": tender_id,
#             "SourceCollection": (
#                 self.source_collection.name
#             ),
#             "SourceDocumentIds": (
#                 source_document_ids
#             ),
#             "SourceDocumentCount": len(
#                 source_documents
#             ),
#             "CopiedSourceDocuments": (
#                 copied_source_documents
#             ),
#             "Input": {
#                 "RawRequirements": (
#                     raw_requirements
#                 ),
#                 "RawRequirementCount": len(
#                     raw_requirements
#                 ),
#             },
#             "Output": None,
#             "Status": "Processing",
#             "IsActive": True,
#             "Error": None,
#             "CreatedAt": created_at,
#             "UpdatedAt": created_at,
#             "CompletedAt": None,
#         }

#         # ----------------------------------------------
#         # Insert destination Mongo document
#         # ----------------------------------------------

#         insert_result = await asyncio.to_thread(
#             self.destination_collection.insert_one,
#             destination_document,
#         )

#         deduplication_id = (
#             insert_result.inserted_id
#         )

#         try:
#             context = {
#                 "CompanyId": company_id,
#                 "TenderId": tender_id,
#                 "DeduplicationId": str(
#                     deduplication_id
#                 ),
#                 "SourceCollection": (
#                     self.source_collection.name
#                 ),
#                 "SourceDocumentIds": (
#                     source_document_ids
#                 ),
#             }

#             # ------------------------------------------
#             # Send requirements to the LLM
#             # ------------------------------------------

#             result = await self.agent.deduplicate(
#                 raw_requirements=raw_requirements,
#                 context=context,
#                 bearer_token=bearer_token,
#                 correlation_id=str(
#                     deduplication_id
#                 ),
#             )

#             completed_at = utc_now()

#             # ------------------------------------------
#             # Save LLM output in destination Mongo
#             # ------------------------------------------

#             await asyncio.to_thread(
#                 self.destination_collection.update_one,
#                 {
#                     "_id": deduplication_id,
#                 },
#                 {
#                     "$set": {
#                         "Output": result,
#                         "Status": "Completed",
#                         "Error": None,
#                         "UpdatedAt": completed_at,
#                         "CompletedAt": completed_at,
#                     }
#                 },
#             )

#             return {
#                 "DeduplicationId": str(
#                     deduplication_id
#                 ),
#                 "Status": "Completed",
#                 "Result": result,
#             }

#         except Exception as exc:
#             failed_at = utc_now()

#             await asyncio.to_thread(
#                 self.destination_collection.update_one,
#                 {
#                     "_id": deduplication_id,
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

#             raise

#     async def get_by_id(
#         self,
#         deduplication_id: str,
#     ) -> dict[str, Any] | None:
#         """
#         Read a saved deduplication result.
#         """

#         if not ObjectId.is_valid(
#             deduplication_id
#         ):
#             return None

#         document = await asyncio.to_thread(
#             self.destination_collection.find_one,
#             {
#                 "_id": ObjectId(
#                     deduplication_id
#                 ),
#             },
#         )

#         if document is None:
#             return None

#         return serialize_mongo_value(
#             document
#         )


from __future__ import annotations
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from bson import ObjectId
from pymongo.collection import Collection

from app.agents.Deduplication_Agent.Agent import (
    RequirementDeduplicationAgent,
)
from app.infrastructure.database import (
    get_deduplication_collection,
    get_requirement_extraction_collection,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def serialize_mongo_value(value: Any) -> Any:
    """
    Convert MongoDB values into JSON-safe values
    for the GET API response.
    """

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


def is_list_value(value: Any) -> bool:
    return isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        (
            str,
            bytes,
            bytearray,
        ),
    )


def normalize_key(value: Any) -> str:
    return (
        str(value)
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
        .lower()
    )


# def extract_requirements_from_document(
#     document: Any,
# ) -> list[Any]:
#     """
#     Find requirements in common MongoDB structures.

#     Supported structures include:

#     1. One requirement stored directly in each MongoDB
#        document using RequirementId and RequirementText.

#     2. Requirement arrays stored under fields such as:
#        RawRequirements
#        Requirements
#        ExtractedRequirements
#        Output.Requirements
#        Result.Requirements
#     """

#     requirement_keys = {
#         "rawrequirements",
#         "requirements",
#         "extractedrequirements",
#         "detectedrequirements",
#         "tenderrequirements",
#         "finalrequirements",
#         "requirementitems",
#     }

#     # Support the current source collection structure,
#     # where every MongoDB document is one requirement.
#     if isinstance(document, Mapping):
#         requirement_text = (
#             document.get("RequirementText")
#             or document.get("requirement_text")
#             or document.get("Text")
#             or document.get("text")
#         )

#         requirement_id = (
#             document.get("RequirementId")
#             or document.get("requirement_id")
#         )

#         if (
#             requirement_text is not None
#             and str(requirement_text).strip()
#         ):
#             return [dict(document)]

#         if (
#             requirement_id is not None
#             and str(requirement_id).strip()
#         ):
#             return [dict(document)]

#     extracted_requirements: list[Any] = []

#     def walk(value: Any) -> None:
#         if isinstance(value, Mapping):
#             for key, child_value in value.items():
#                 normalized_key = normalize_key(key)

#                 if normalized_key in requirement_keys:
#                     if is_list_value(child_value):
#                         for requirement in child_value:
#                             if requirement is not None:
#                                 extracted_requirements.append(
#                                     requirement
#                                 )

#                     elif child_value is not None:
#                         extracted_requirements.append(
#                             child_value
#                         )

#                 else:
#                     walk(child_value)

#         elif is_list_value(value):
#             for child_value in value:
#                 walk(child_value)

#     walk(document)

#     return extracted_requirements

def extract_requirements_from_document(
    document: Any,
) -> list[Any]:
    """
    Find requirements in common MongoDB structures.

    Supports:

    1. One requirement per MongoDB document.
    2. Requirement arrays such as RawRequirements.
    3. Nested requirement arrays such as Output.Requirements.

    All MongoDB ObjectId and datetime values are converted
    into JSON-safe values before requirements are passed to
    the agent.
    """

    requirement_keys = {
        "rawrequirements",
        "requirements",
        "extractedrequirements",
        "detectedrequirements",
        "tenderrequirements",
        "finalrequirements",
        "requirementitems",
    }

    extracted_requirements: list[Any] = []

    # --------------------------------------------------
    # One MongoDB document represents one requirement
    # --------------------------------------------------

    if isinstance(document, Mapping):
        requirement_text = (
            document.get("RequirementText")
            or document.get("requirement_text")
            or document.get("requirementText")
            or document.get("Text")
            or document.get("text")
        )

        requirement_id = (
            document.get("RequirementId")
            or document.get("requirement_id")
            or document.get("requirementId")
        )

        if requirement_text or requirement_id:
            requirement_document = dict(document)

            source_mongo_id = requirement_document.pop(
                "_id",
                None,
            )

            if source_mongo_id is not None:
                requirement_document[
                    "SourceMongoId"
                ] = str(source_mongo_id)

            return [
                serialize_mongo_value(
                    requirement_document
                )
            ]

    # --------------------------------------------------
    # Requirement arrays inside MongoDB documents
    # --------------------------------------------------

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child_value in value.items():
                normalized_key = normalize_key(key)

                if normalized_key in requirement_keys:
                    if is_list_value(child_value):
                        for requirement in child_value:
                            if requirement is not None:
                                cleaned_requirement = (
                                    serialize_mongo_value(
                                        requirement
                                    )
                                )

                                if isinstance(
                                    cleaned_requirement,
                                    Mapping,
                                ):
                                    cleaned_requirement = dict(
                                        cleaned_requirement
                                    )

                                    source_mongo_id = (
                                        cleaned_requirement.pop(
                                            "_id",
                                            None,
                                        )
                                    )

                                    if (
                                        source_mongo_id
                                        is not None
                                    ):
                                        cleaned_requirement[
                                            "SourceMongoId"
                                        ] = str(
                                            source_mongo_id
                                        )

                                extracted_requirements.append(
                                    cleaned_requirement
                                )

                    elif child_value is not None:
                        cleaned_requirement = (
                            serialize_mongo_value(
                                child_value
                            )
                        )

                        if isinstance(
                            cleaned_requirement,
                            Mapping,
                        ):
                            cleaned_requirement = dict(
                                cleaned_requirement
                            )

                            source_mongo_id = (
                                cleaned_requirement.pop(
                                    "_id",
                                    None,
                                )
                            )

                            if source_mongo_id is not None:
                                cleaned_requirement[
                                    "SourceMongoId"
                                ] = str(
                                    source_mongo_id
                                )

                        extracted_requirements.append(
                            cleaned_requirement
                        )

                else:
                    walk(child_value)

        elif is_list_value(value):
            for child_value in value:
                walk(child_value)

    walk(document)

    return extracted_requirements
    
def requirement_identity(
    requirement: Any,
) -> str:
    """
    Remove only exact duplicate input objects.

    Similar requirements must remain because the
    LLM is responsible for semantic deduplication.
    """

    if isinstance(requirement, Mapping):
        for key in (
            "RequirementId",
            "requirement_id",
            "Id",
            "id",
            "_id",
        ):
            requirement_id = requirement.get(key)

            if requirement_id is not None:
                requirement_id_text = str(
                    requirement_id
                ).strip()

                if requirement_id_text:
                    return f"id:{requirement_id_text}"

    return json.dumps(
        requirement,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def remove_exact_duplicates(
    requirements: list[Any],
) -> list[Any]:
    result: list[Any] = []
    identities: set[str] = set()

    for requirement in requirements:
        identity = requirement_identity(
            requirement
        )

        if identity in identities:
            continue

        identities.add(identity)
        result.append(requirement)

    return result


def prepare_document_for_copy(
    source_document: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Prepare a source document for copying into the
    deduplication destination document.

    The source _id is renamed because the destination
    record has its own _id.
    """

    copied_document = dict(source_document)

    source_id = copied_document.pop(
        "_id",
        None,
    )

    return {
        "SourceMongoId": (
            str(source_id)
            if source_id is not None
            else None
        ),
        "Document": copied_document,
    }


class RequirementDeduplicationService:
    def __init__(
        self,
        source_collection: Collection | None = None,
        destination_collection: Collection | None = None,
        agent: RequirementDeduplicationAgent | None = None,
    ) -> None:
        self._source_collection = source_collection
        self._destination_collection = (
            destination_collection
        )
        self._agent = agent

    @property
    def source_collection(self) -> Collection:
        """
        Input/source collection:

        TenderRequirementExtractions
        """

        if self._source_collection is None:
            self._source_collection = (
                get_requirement_extraction_collection()
            )

        return self._source_collection

    @property
    def destination_collection(self) -> Collection:
        """
        Output/destination collection:

        TenderRequirementDeduplications
        """

        if self._destination_collection is None:
            self._destination_collection = (
                get_deduplication_collection()
            )

        return self._destination_collection

    @property
    def collection(self) -> Collection:
        """
        Compatibility property for existing code.
        """

        return self.destination_collection

    @property
    def agent(self) -> RequirementDeduplicationAgent:
        if self._agent is None:
            self._agent = (
                RequirementDeduplicationAgent()
            )

        return self._agent

    def build_source_query(
        self,
        company_id: str,
        tender_id: str,
    ) -> dict[str, Any]:
        """
        Supports both string IDs and Mongo ObjectIds,
        along with common field-name variations.
        """

        company_values: list[Any] = [
            company_id
        ]

        tender_values: list[Any] = [
            tender_id
        ]

        if ObjectId.is_valid(company_id):
            company_values.append(
                ObjectId(company_id)
            )

        if ObjectId.is_valid(tender_id):
            tender_values.append(
                ObjectId(tender_id)
            )

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

    async def read_source_documents(
        self,
        company_id: str,
        tender_id: str,
    ) -> list[dict[str, Any]]:
        """
        Read input documents from
        TenderRequirementExtractions.
        """

        query = self.build_source_query(
            company_id=company_id,
            tender_id=tender_id,
        )

        print(
            "Source database:",
            self.source_collection.database.name,
        )

        print(
            "Source collection:",
            self.source_collection.name,
        )

        print(
            "Source query:",
            query,
        )

        def read_documents() -> list[
            dict[str, Any]
        ]:
            return list(
                self.source_collection
                .find(query)
                .sort("_id", -1)
            )

        source_documents = await asyncio.to_thread(
            read_documents
        )

        print(
            "Source documents found:",
            len(source_documents),
        )

        if not source_documents:
            raise ValueError(
                "No source documents were found for "
                "the supplied CompanyId and TenderId. "
                f"Database: "
                f"{self.source_collection.database.name}. "
                f"Collection: "
                f"{self.source_collection.name}. "
                f"CompanyId: {company_id}. "
                f"TenderId: {tender_id}."
            )

        return source_documents

    async def process(
        self,
        request: Any,
        bearer_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Main method called by deduplication_route.py.

        Flow:

        1. Read CompanyId and TenderId.
        2. Read source Mongo documents.
        3. Extract RawRequirements.
        4. Insert processing record in destination.
        5. Send requirements to the LLM.
        6. Save LLM output in destination.
        """

        if hasattr(request, "model_dump"):
            payload = request.model_dump(
                mode="python"
            )

        elif isinstance(request, Mapping):
            payload = dict(request)

        else:
            raise ValueError(
                "Request must be a Pydantic model "
                "or dictionary"
            )

        company_id = str(
            payload.get(
                "CompanyId",
                "",
            )
        ).strip()

        tender_id = str(
            payload.get(
                "TenderId",
                "",
            )
        ).strip()

        if not company_id:
            raise ValueError(
                "CompanyId is required"
            )

        if not tender_id:
            raise ValueError(
                "TenderId is required"
            )

        # ----------------------------------------------
        # Read source Mongo documents
        # ----------------------------------------------

        source_documents = (
            await self.read_source_documents(
                company_id=company_id,
                tender_id=tender_id,
            )
        )

        raw_requirements: list[Any] = []
        source_document_ids: list[str] = []
        copied_source_documents: list[
            dict[str, Any]
        ] = []

        for source_document in source_documents:
            source_id = source_document.get(
                "_id"
            )

            if source_id is not None:
                source_document_ids.append(
                    str(source_id)
                )

            copied_source_documents.append(
                prepare_document_for_copy(
                    source_document
                )
            )

            requirements = (
                extract_requirements_from_document(
                    source_document
                )
            )

            raw_requirements.extend(
                requirements
            )

        raw_requirements = remove_exact_duplicates(
            raw_requirements
        )

        if not raw_requirements:
            raise ValueError(
                "Source documents were found, but "
                "no requirements were found. "
                "Expected a top-level RequirementText, "
                "RawRequirements, Requirements, "
                "ExtractedRequirements or "
                "Output.Requirements."
            )

        created_at = utc_now()

        destination_document = {
            "CompanyId": company_id,
            "TenderId": tender_id,
            "SourceCollection": (
                self.source_collection.name
            ),
            "SourceDocumentIds": (
                source_document_ids
            ),
            "SourceDocumentCount": len(
                source_documents
            ),
            "CopiedSourceDocuments": (
                copied_source_documents
            ),
            "Input": {
                "RawRequirements": (
                    raw_requirements
                ),
                "RawRequirementCount": len(
                    raw_requirements
                ),
            },
            "Output": None,
            "Status": "Processing",
            "IsActive": True,
            "Error": None,
            "CreatedAt": created_at,
            "UpdatedAt": created_at,
            "CompletedAt": None,
        }

        # ----------------------------------------------
        # Insert destination Mongo document
        # ----------------------------------------------

        insert_result = await asyncio.to_thread(
            self.destination_collection.insert_one,
            destination_document,
        )

        deduplication_id = (
            insert_result.inserted_id
        )

        try:
            context = {
                "CompanyId": company_id,
                "TenderId": tender_id,
                "DeduplicationId": str(
                    deduplication_id
                ),
                "SourceCollection": (
                    self.source_collection.name
                ),
                "SourceDocumentIds": (
                    source_document_ids
                ),
            }

            # ------------------------------------------
            # Send requirements to the LLM
            # ------------------------------------------

            result = await self.agent.deduplicate(
                raw_requirements=raw_requirements,
                context=context,
                bearer_token=bearer_token,
                correlation_id=str(
                    deduplication_id
                ),
            )

            completed_at = utc_now()

            # ------------------------------------------
            # Save LLM output in destination Mongo
            # ------------------------------------------

            await asyncio.to_thread(
                self.destination_collection.update_one,
                {
                    "_id": deduplication_id,
                },
                {
                    "$set": {
                        "Output": result,
                        "Status": "Completed",
                        "Error": None,
                        "UpdatedAt": completed_at,
                        "CompletedAt": completed_at,
                    }
                },
            )

            return {
                "DeduplicationId": str(
                    deduplication_id
                ),
                "Status": "Completed",
                "Result": result,
            }

        except Exception as exc:
            failed_at = utc_now()

            await asyncio.to_thread(
                self.destination_collection.update_one,
                {
                    "_id": deduplication_id,
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

            raise

    async def get_by_id(
        self,
        deduplication_id: str,
    ) -> dict[str, Any] | None:
        """
        Read a saved deduplication result.
        """

        if not ObjectId.is_valid(
            deduplication_id
        ):
            return None

        document = await asyncio.to_thread(
            self.destination_collection.find_one,
            {
                "_id": ObjectId(
                    deduplication_id
                ),
            },
        )

        if document is None:
            return None

        return serialize_mongo_value(
            document
        )