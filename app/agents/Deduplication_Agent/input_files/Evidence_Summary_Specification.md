# Evidence Summary Agent Specification

Version: 2.0

## PURPOSE

This file controls the Evidence Summary LLM response structure.

The response must be strict, valid JSON.

Do not return markdown, code fences, comments, explanations or reasoning.

## LLM RESPONSE SCHEMA

The Evidence Summary LLM must return exactly this structure for one deduplicated requirement:

{
"EvidenceFound": false,
"EvidenceReason": "The supplied evidence does not directly demonstrate the required obligation.",
"EvidenceSummary": "",
"EvidenceConfidence": 0.0,
"MissingEvidenceReason": "A documented policy, process, certification, control, commitment or project record supporting the requirement is missing.",
"SupportingEvidenceIds": []
}

## ALLOWED FIELDS

Return exactly these fields:

* EvidenceFound
* EvidenceReason
* EvidenceSummary
* EvidenceConfidence
* MissingEvidenceReason
* SupportingEvidenceIds

Do not add any other fields.

## EVIDENCEFOUND

Type: boolean

Allowed values:

* true
* false

Set EvidenceFound to true only when at least one supplied evidence chunk directly and materially supports the complete requirement.

Set EvidenceFound to false when:

* no direct evidence exists
* evidence is generic marketing language
* evidence supports only the general topic
* evidence supports only part of the requirement
* evidence is unrelated
* evidence requires inference
* evidence omits a material condition
* evidence concerns a different obligation
* no valid SupportingEvidenceId exists

## EVIDENCE REASON

Type: string

EvidenceReason must:

* be non-empty
* explain the evidence decision
* refer to the supplied evidence
* remain concise
* identify direct support or the specific evidence gap
* avoid unsupported interpretation

EvidenceReason must not use inference wording such as:

* implies
* suggests
* indicates a commitment
* broadly supports
* appears to support
* likely demonstrates
* could mean
* generally aligns

## EVIDENCE SUMMARY

Type: string

When EvidenceFound is true:

* EvidenceSummary must be non-empty
* summarise only directly supported facts
* connect those facts to the requirement
* not add facts absent from the supplied evidence
* not include promotional or proposal-writing language

When EvidenceFound is false:

* EvidenceSummary must be an empty string

## EVIDENCE CONFIDENCE

Type: number

Allowed range:

* 0.0 to 1.0

Rules:

* return 0.0 when EvidenceFound is false
* use 0.90 to 1.00 for explicit, direct and authoritative evidence
* use 0.75 to 0.89 for direct and specific evidence with minor limitations
* use 0.60 to 0.74 for relevant evidence that is direct but less authoritative
* never return high confidence for generic marketing claims
* duplicate evidence must not increase confidence

## MISSING EVIDENCE REASON

Type: string or null

When EvidenceFound is true:

* MissingEvidenceReason must be null

When EvidenceFound is false:

* MissingEvidenceReason must be a non-empty string
* clearly state what evidence is missing
* identify the missing policy, process, certification, control, commitment, methodology, record, project example or measurable result

Do not return vague messages such as:

* more evidence is required
* evidence is insufficient
* no relevant information was found

State the specific missing evidence.

## SUPPORTING EVIDENCE IDS

Type: array of strings

When EvidenceFound is true:

* include only EvidenceId values from supplied chunks
* include only chunks that directly support the requirement
* include at least one ID
* exclude unrelated retrieved candidates
* exclude duplicate IDs
* exclude IDs whose EvidenceText duplicates another selected source without adding new support

When EvidenceFound is false:

* return an empty array

Do not invent EvidenceId values.

## COMPLETE REQUIREMENT VALIDATION

When the requirement contains multiple material obligations, all material obligations must be supported.

If only part of the requirement is supported:

* EvidenceFound must be false
* EvidenceSummary must be empty
* EvidenceConfidence must be 0.0
* MissingEvidenceReason must identify the unsupported obligation
* SupportingEvidenceIds must be empty

## GENERIC MARKETING VALIDATION

Generic statements are not direct evidence.

Examples include:

* Risk Mitigation & Compliance Assurance
* Uncompromising Quality & Reliability
* Professional Finesse
* Proven Expertise
* Secure and Future-Ready Systems
* Faster Time to Value
* Industry Leadership
* End-to-End Capability

These statements must not produce EvidenceFound true unless another supplied chunk contains direct, specific supporting evidence.

## FALSE RESULT EXAMPLE

Requirement:

“The supplier must ensure that all deliverables comply with applicable law.”

Supplied evidence:

“Risk Mitigation & Compliance Assurance.”

Required response:

{
"EvidenceFound": false,
"EvidenceReason": "The supplied text is a generic marketing statement and does not directly demonstrate that all deliverables comply with applicable law.",
"EvidenceSummary": "",
"EvidenceConfidence": 0.0,
"MissingEvidenceReason": "A documented legal-compliance policy, process, assurance statement or contractual control covering deliverables is missing.",
"SupportingEvidenceIds": []
}

## TRUE RESULT EXAMPLE

Requirement:

“The supplier must maintain ISO 27001 certification.”

Supplied evidence:

EvidenceId: EVIDENCE-SOURCE-001

EvidenceText:

“The organisation maintains ISO 27001 certification under certificate ABC-123, valid until 31 December 2027.”

Valid response:

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

## PARTIAL EVIDENCE EXAMPLE

Requirement:

“The supplier must maintain ISO 27001 certification and provide annual audit reports.”

Supplied evidence:

“The organisation maintains ISO 27001 certification.”

Required response:

{
"EvidenceFound": false,
"EvidenceReason": "The supplied evidence confirms ISO 27001 certification but does not demonstrate that annual audit reports are provided.",
"EvidenceSummary": "",
"EvidenceConfidence": 0.0,
"MissingEvidenceReason": "Evidence demonstrating the provision of annual audit reports is missing.",
"SupportingEvidenceIds": []
}

## APPLICATION OUTPUT ITEM

After validating the LLM response, the application may build the complete MongoDB item:

{
"EvidenceSummaryItemId": "EVIDENCE-0001",
"DeduplicatedRequirementId": "DEDUP-GROUP-0001",
"RequirementIds": [
"REQ-001",
"REQ-002"
],
"CanonicalRequirement": "The supplier shall maintain ISO 27001 certification.",
"RequirementType": "Compliance",
"IntentResult": {
"CapabilityIntent": [],
"EvidenceSections": [],
"SemanticAnchors": []
},
"EvidenceFound": true,
"EvidenceSources": [
{
"EvidenceId": "EVIDENCE-SOURCE-001",
"ChunkId": "CHUNK-001",
"SourceTitle": "Information Security Policy",
"SourceDocument": "Security Policy.pdf",
"DocumentType": "Policy",
"RelatedSection": "Certifications",
"EvidenceText": "The organisation maintains ISO 27001 certification.",
"EvidenceScore": 0.82,
"EvidenceDate": "2026-07-15T11:51:29.690857"
}
],
"EvidenceReason": "The supplied security policy explicitly confirms that the organisation maintains ISO 27001 certification.",
"EvidenceSummary": "The organisation maintains ISO 27001 certification, directly supporting the certification requirement.",
"EvidenceConfidence": 0.95,
"MissingEvidenceReason": null,
"Status": "IsRegenerated"
}

The application, not the LLM, should add:

* EvidenceSummaryItemId
* DeduplicatedRequirementId
* RequirementIds
* CanonicalRequirement
* RequirementType
* IntentResult
* EvidenceSources
* Status

The application must build EvidenceSources only from the SupportingEvidenceIds returned by the LLM.

## APPLICATION FILTERING RULE

Before saving the final item:

1. Validate every SupportingEvidenceId against the supplied Qdrant results.
2. Reject unknown EvidenceId values.
3. Remove duplicate SupportingEvidenceIds.
4. Build EvidenceSources only from validated SupportingEvidenceIds.
5. When EvidenceFound is false, save EvidenceSources as an empty array.
6. Do not save all Qdrant candidates as EvidenceSources.
7. Do not allow duplicate EvidenceText to increase confidence.

## VALIDATION RULES

A valid response requires:

1. EvidenceFound is a boolean.
2. EvidenceReason is a non-empty string.
3. EvidenceConfidence is between 0 and 1.
4. When EvidenceFound is true:

   * EvidenceSummary is non-empty.
   * MissingEvidenceReason is null.
   * SupportingEvidenceIds contains at least one supplied EvidenceId.
5. When EvidenceFound is false:

   * EvidenceSummary is empty.
   * EvidenceConfidence is 0.0.
   * MissingEvidenceReason is non-empty.
   * SupportingEvidenceIds is empty.
6. Every SupportingEvidenceId exists in the supplied evidence.
7. No unsupported field is returned.
8. The response is parseable using json.loads().
9. Generic marketing text alone must not produce EvidenceFound true.
10. Partial evidence must not produce EvidenceFound true.

## JSON RULES

1. Return one JSON object only.
2. Use double quotes for property names and string values.
3. Do not include trailing commas.
4. Do not include markdown fences.
5. Do not include comments.
6. Do not include reasoning.
7. Do not add extra properties.
8. Do not return null for required strings or arrays.
