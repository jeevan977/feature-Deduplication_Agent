# Requirement Deduplication Specification File

Version: 1.0

## OBJECTIVE

Controls ONLY output structure.

Return STRICT JSON.

No markdown.

No explanations.

## OUTPUT SCHEMA

{
  "DeduplicationStatus": "",
  "CanonicalRequirements": [
    {
      "CanonicalRequirementId": "",
      "CanonicalRequirementText": "",
      "RequirementType": "",
      "MandatoryFlag": false,
      "SourceRequirements": [],
      "SourceDocuments": [],
      "DuplicateCount": 0
    }
  ]
}

## DeduplicationStatus

Return:

- Deduplicated
- NoDuplicatesFound

## RULES

1. Strict JSON only
2. Preserve lineage
3. Valid schema mandatory
4. No reasoning output
5. CanonicalRequirementText must preserve meaning
