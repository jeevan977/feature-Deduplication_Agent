# Requirement Deduplication Specification

Version: 2.0

## PURPOSE

This file controls only the LLM response structure.

The response must be strict, valid JSON.

Do not return markdown, code fences, explanations, comments or reasoning.

## SUCCESS OUTPUT SCHEMA

```json
{
  "DeduplicationStatus": "Deduplicated",
  "DeduplicatedRequirements": [
    {
      "CanonicalRequirement": "The supplier shall maintain ISO 27001 certification.",
      "RequirementIds": [
        "REQ-001",
        "REQ-044"
      ],
      "RequirementType": "Compliance"
    }
  ],
  "ValidationError": null
}
```

## NO-DUPLICATES OUTPUT SCHEMA

```json
{
  "DeduplicationStatus": "NoDuplicatesFound",
  "DeduplicatedRequirements": [
    {
      "CanonicalRequirement": "The supplier shall maintain ISO 27001 certification.",
      "RequirementIds": [
        "REQ-001"
      ],
      "RequirementType": "Compliance"
    }
  ],
  "ValidationError": null
}
```

Even when no duplicates are found, every input requirement must still appear in `DeduplicatedRequirements`.

## VALIDATION-ERROR OUTPUT SCHEMA

```json
{
  "DeduplicationStatus": "ValidationError",
  "DeduplicatedRequirements": [],
  "ValidationError": {
    "Code": "REQUIREMENT_ID_COVERAGE_ERROR",
    "Message": "Unable to return every input RequirementId exactly once.",
    "MissingRequirementIds": [],
    "RepeatedRequirementIds": [],
    "UnknownRequirementIds": []
  }
}
```

## FIELD RULES

### DeduplicationStatus

Allowed values:

* `Deduplicated`
* `NoDuplicatesFound`
* `ValidationError`

Use `Deduplicated` when at least one output item contains more than one RequirementId.

Use `NoDuplicatesFound` when every output item contains exactly one RequirementId.

Use `ValidationError` only when valid RequirementId coverage cannot be produced.

### DeduplicatedRequirements

Must contain every canonical and unique requirement.

Do not return only duplicate groups.

Each item must contain exactly these fields:

* `CanonicalRequirement`
* `RequirementIds`
* `RequirementType`

Do not add extra fields.

### CanonicalRequirement

Must:

* be a non-empty string
* preserve the source procurement meaning
* normally match one supplied RequirementText
* preserve material conditions
* preserve mandatory strength
* preserve numbers, dates, standards and service levels
* not contain invented wording

### RequirementIds

Must:

* be a non-empty array
* contain only supplied RequirementIds
* contain each original RequirementId exactly once across the complete response
* include all IDs belonging to the duplicate group
* contain one ID for a unique requirement
* contain no duplicate values

### RequirementType

Must:

* be a non-empty string
* match the input RequirementType
* be the same for every RequirementId in the output item
* never combine requirements from different types

### ValidationError

Must be `null` for successful responses.

For a validation error, it must contain:

* `Code`
* `Message`
* `MissingRequirementIds`
* `RepeatedRequirementIds`
* `UnknownRequirementIds`

## STRICT COVERAGE RULE

Let the complete set of input RequirementIds be `INPUT_IDS`.

Let all RequirementIds returned across `DeduplicatedRequirements` be `OUTPUT_IDS`.

A valid response requires:

* every `INPUT_IDS` value appears in `OUTPUT_IDS`
* every input ID appears exactly once
* no additional ID appears
* `INPUT_IDS` and `OUTPUT_IDS` represent the same complete set

Do not silently create unique items for IDs accidentally omitted from the response.

## ORDERING RULE

Return output items according to the first appearance of their RequirementIds in the input.

Within each `RequirementIds` array, preserve the original input order.

## JSON RULES

1. Return one JSON object only.
2. Use double quotes for property names and string values.
3. Do not include trailing commas.
4. Do not return markdown fences.
5. Do not return null instead of required arrays.
6. Do not include analysis or reasoning.
7. Do not include additional properties.
8. Ensure the response can be parsed directly by `json.loads()`.
