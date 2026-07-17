# User Prompt – Requirement Deduplication Agent

Version: 2.0

## INPUTS

You will receive:

1. Requirement Deduplication Constitution
2. Requirement Deduplication Specification
3. Normalised tender requirements

The requirements have already been extracted.

Do not perform requirement extraction.

## TASK

Analyse all supplied requirements in this single request.

First consolidate exact duplicate requirements.

Then identify requirements that are genuinely semantically equivalent.

Create one canonical output item for each duplicate group and one output item for each unique requirement.

Do not target or force a predefined number of output requirements.

## INPUT FIELDS

The input contains only:

* RequirementId
* RequirementText
* RequirementType

The input may use compact classification codes to reduce tokens.

Example:

```json
{
  "TypeLegend": {
    "T1": "Compliance",
    "T2": "Contract"
  },
  "ClassifiedRequirements": {
    "T1": [
      [
        [
          "REQ-001",
          "REQ-044"
        ],
        "The supplier shall maintain ISO 27001 certification."
      ]
    ],
    "T2": [
      [
        [
          "REQ-100"
        ],
        "The supplier shall provide a mobilisation plan."
      ]
    ]
  }
}
```

`TypeLegend` maps each classification code to the real RequirementType.

Each classified row contains:

```json
[
  [
    "RequirementId-1",
    "RequirementId-2"
  ],
  "RequirementText"
]
```

A row may contain multiple RequirementIds when exact duplicate texts were compressed before this request.

All IDs in that row must remain together unless doing so would violate the Constitution.

## EXECUTION RULES

1. Process the complete supplied input.
2. Do not create candidate partitions.
3. Do not request additional input.
4. Do not omit difficult requirements.
5. Do not force a target deduplication count.
6. Consolidate exact duplicate text.
7. Consolidate semantic duplicates only when the obligation is equivalent.
8. Do not merge requirements with different RequirementType values.
9. Do not merge related but distinct obligations.
10. Preserve all original RequirementIds.
11. Return every original RequirementId exactly once.
12. Do not create new RequirementIds.
13. Do not invent canonical wording.
14. Preserve values, dates, standards, timelines and mandatory strength.
15. Return unique requirements as single-ID output items.

## CANONICAL WORDING

For each duplicate group:

* select the clearest and strongest faithful source wording
* prefer a complete source RequirementText
* do not combine unrelated clauses
* do not broaden the obligation
* do not remove material conditions
* do not add proposal or explanatory wording

## FINAL VALIDATION

Before returning the response, verify:

* every supplied RequirementId is present
* every RequirementId appears exactly once
* no unknown RequirementId is present
* all exact duplicates have been consolidated
* all semantic groups contain equivalent obligations
* no group contains different RequirementType values
* unique requirements are included
* the response follows the Specification File exactly

If any RequirementId is missing, repeated or unknown, return the Specification-defined `ValidationError` response.

Do not silently treat missing IDs as unique.

## OUTPUT

Return only strict JSON matching the Requirement Deduplication Specification.

Do not return markdown.

Do not return code fences.

Do not return explanations.

Do not return analysis or reasoning.
