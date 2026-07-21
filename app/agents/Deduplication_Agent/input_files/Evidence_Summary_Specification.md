# Evidence Summary Agent Specification

Version: 2.1

## 1. Purpose

This file defines the exact LLM response structure for one deduplicated
requirement.

Return strict, valid JSON only. Do not return Markdown, code fences,
reasoning, comments or additional fields.

## 2. Required LLM Response Schema

Return exactly:

```json
{
  "EvidenceFound": false,
  "EvidenceReason": "No supplied evidence chunk directly supports the complete requirement.",
  "EvidenceSummary": "",
  "EvidenceConfidence": 0.0,
  "MissingEvidenceReason": "A documented policy, process, certification, control, record or project example supporting the requirement is missing.",
  "SupportingEvidenceIds": []
}
```

## 3. Allowed Fields

Return exactly these six fields:

- `EvidenceFound`
- `EvidenceReason`
- `EvidenceSummary`
- `EvidenceConfidence`
- `MissingEvidenceReason`
- `SupportingEvidenceIds`

Do not add any other field.

## 4. EvidenceFound

Type: boolean.

Set to `true` only when:

- at least one supplied evidence chunk directly supports the requirement;
- all material parts of the requirement are supported;
- the decision requires no unsupported inference;
- at least one valid supplied EvidenceId can be returned.

Set to `false` when:

- no evidence chunks were supplied;
- no direct evidence exists;
- evidence is generic, partial, unrelated or about a different obligation;
- evidence omits a material condition;
- the decision requires inference;
- no valid supporting EvidenceId exists;
- the requirement is a submission, declaration, form-completion or
  contract-acceptance action for which company evidence is not applicable.

## 5. EvidenceReason

Type: non-empty string.

It must:

- explain the decision concisely;
- refer to the supplied evidence or state that none was supplied;
- identify direct support, a specific gap, partial support or
  non-applicability;
- avoid unsupported interpretation.

Do not use inference wording such as:

- implies;
- suggests;
- likely;
- appears to support;
- broadly supports;
- generally aligns.

### Non-applicable example

```json
"EvidenceReason": "This is a tender submission instruction and does not require supporting company evidence."
```

## 6. EvidenceSummary

Type: string.

When `EvidenceFound` is `true`:

- return a concise factual summary;
- use only facts stated in selected evidence;
- connect those facts directly to the requirement;
- do not add proposal or marketing language.

When `EvidenceFound` is `false`:

```json
"EvidenceSummary": ""
```

## 7. EvidenceConfidence

Type: number from `0.0` to `1.0`.

Use:

- `0.90` to `1.00`: explicit, direct and authoritative;
- `0.75` to `0.89`: direct and specific with minor limitations;
- `0.60` to `0.74`: direct but less authoritative;
- `0.0`: every negative or non-applicable result.

Duplicate evidence must not increase confidence.

## 8. MissingEvidenceReason

Type: string or null.

When `EvidenceFound` is `true`:

```json
"MissingEvidenceReason": null
```

When evidence is applicable but missing:

- return a non-empty string;
- identify the specific missing policy, process, certification, control,
  methodology, record, project example or measurable result;
- do not use vague text such as “more evidence is needed”.

When company evidence is not applicable:

- return a non-empty action-based explanation.

Example:

```json
"MissingEvidenceReason": "Not applicable: this requirement must be satisfied by completing the tender submission worksheet."
```

## 9. SupportingEvidenceIds

Type: array of strings.

When `EvidenceFound` is `true`:

- include at least one EvidenceId supplied in the current prompt;
- include only directly supporting evidence;
- exclude unrelated candidates;
- exclude duplicate IDs;
- exclude duplicate evidence text that adds no new support.

When `EvidenceFound` is `false`:

```json
"SupportingEvidenceIds": []
```

Never invent an EvidenceId.

## 10. Complete-Requirement Validation

When the requirement contains multiple material obligations, all must be
supported.

When only part is supported, return:

```json
{
  "EvidenceFound": false,
  "EvidenceReason": "The supplied evidence supports part of the requirement but does not support all material obligations.",
  "EvidenceSummary": "",
  "EvidenceConfidence": 0.0,
  "MissingEvidenceReason": "Evidence supporting the remaining material obligation is missing.",
  "SupportingEvidenceIds": []
}
```

The reason should name the unsupported obligation whenever possible.

## 11. Generic Marketing Validation

Generic marketing text alone must not produce a positive result.

Examples:

- proven expertise;
- professional excellence;
- secure and future-ready systems;
- risk mitigation;
- compliance assurance;
- quality and reliability;
- faster time to value;
- end-to-end capability.

## 12. Response Examples

### Direct evidence found

Requirement:

`The supplier must maintain ISO 27001 certification.`

Supplied evidence:

- EvidenceId: `EVIDENCE-SOURCE-001`
- EvidenceText: `The organisation maintains ISO 27001 certification under certificate ABC-123, valid until 31 December 2027.`

Response:

```json
{
  "EvidenceFound": true,
  "EvidenceReason": "The supplied certification record explicitly confirms that the organisation maintains ISO 27001 certification.",
  "EvidenceSummary": "The organisation holds ISO 27001 certification under certificate ABC-123, valid until 31 December 2027.",
  "EvidenceConfidence": 0.98,
  "MissingEvidenceReason": null,
  "SupportingEvidenceIds": [
    "EVIDENCE-SOURCE-001"
  ]
}
```

### No direct evidence

```json
{
  "EvidenceFound": false,
  "EvidenceReason": "The supplied evidence does not directly demonstrate the required worker-vetting process.",
  "EvidenceSummary": "",
  "EvidenceConfidence": 0.0,
  "MissingEvidenceReason": "A documented worker-vetting policy, procedure or verification record is missing.",
  "SupportingEvidenceIds": []
}
```

### No evidence chunks supplied

```json
{
  "EvidenceFound": false,
  "EvidenceReason": "No company evidence chunks were supplied for evaluation.",
  "EvidenceSummary": "",
  "EvidenceConfidence": 0.0,
  "MissingEvidenceReason": "Company evidence directly supporting the requirement is unavailable.",
  "SupportingEvidenceIds": []
}
```

### Submission instruction: evidence not applicable

Requirement:

`Complete the Total Cost of Delivery Worksheet.`

Response:

```json
{
  "EvidenceFound": false,
  "EvidenceReason": "This is a tender submission instruction and does not require supporting company evidence.",
  "EvidenceSummary": "",
  "EvidenceConfidence": 0.0,
  "MissingEvidenceReason": "Not applicable: this requirement must be satisfied by completing the Total Cost of Delivery Worksheet.",
  "SupportingEvidenceIds": []
}
```

### Contract acceptance: evidence not applicable

Requirement:

`The Supplier must accept the confidentiality clause.`

Response:

```json
{
  "EvidenceFound": false,
  "EvidenceReason": "This is a contract-acceptance requirement rather than a request for existing company evidence.",
  "EvidenceSummary": "",
  "EvidenceConfidence": 0.0,
  "MissingEvidenceReason": "Not applicable: this requirement must be addressed through the legal or contract response.",
  "SupportingEvidenceIds": []
}
```

## 13. Application Responsibilities

The application, not the LLM, adds:

- `EvidenceSummaryItemId`;
- `CanonicalRequirementId`;
- `RequirementIds`;
- `CanonicalRequirement`;
- `RequirementType`;
- `IntentResult`;
- `EvidenceSources`;
- operational `Status`.

The application must:

1. validate every returned SupportingEvidenceId against supplied Qdrant
   results;
2. reject unknown IDs;
3. remove duplicate IDs and duplicate evidence text;
4. build EvidenceSources only from validated supporting IDs;
5. save an empty EvidenceSources array when EvidenceFound is false;
6. never save all retrieved candidates automatically;
7. preserve one output item for every canonical requirement.

## 14. Final Validation Rules

A valid LLM response requires:

1. exactly the six allowed fields;
2. `EvidenceFound` is boolean;
3. `EvidenceReason` is non-empty;
4. `EvidenceConfidence` is between `0.0` and `1.0`;
5. positive result:
   - non-empty EvidenceSummary;
   - null MissingEvidenceReason;
   - at least one valid SupportingEvidenceId;
6. negative result:
   - empty EvidenceSummary;
   - confidence `0.0`;
   - non-empty MissingEvidenceReason;
   - empty SupportingEvidenceIds;
7. no invented or unknown EvidenceId;
8. no generic marketing-only positive result;
9. no partial-evidence positive result;
10. directly parseable JSON.

## 15. JSON Rules

1. Return one JSON object only.
2. Use double quotes for property names and string values.
3. Do not include trailing commas.
4. Do not include Markdown fences.
5. Do not include comments or reasoning.
6. Do not add extra properties.
7. Do not return null for required strings or arrays.