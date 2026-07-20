# Requirement Deduplication Specification

Version: 2.1

## 1. Purpose

This file defines the LLM task, input interpretation and response structure
for Requirement Deduplication.

Follow the Requirement Deduplication Constitution for all semantic decisions.

Return one strict JSON object only. Do not return Markdown, code fences,
reasoning, comments or explanations outside the JSON.

## 2. Runtime Task

Analyse all supplied requirements together and identify:

- genuine duplicate groups;
- requirements that are not duplicates.

Use:

- `RequirementText` as the primary source of meaning;
- `RequirementType` as supporting context;
- `RequirementId` only for traceability.

A false merge is more harmful than a missed duplicate. When uncertain, keep
requirements separate.

## 3. Input Fields

Each runtime requirement contains:

- `RequirementId`
- `RequirementText`
- `RequirementType`

Use only the supplied RequirementIds. Do not create or modify RequirementIds.

## 4. Required Output Schema

Return exactly this structure:

```json
{
  "DuplicateGroups": [
    {
      "CanonicalRequirement": "Complete standalone requirement",
      "RequirementIds": [
        "REQ-001",
        "REQ-044"
      ],
      "Reason": "Brief explanation of why the requirements express the same complete material obligation."
    }
  ],
  "UniqueRequirementIds": [
    "REQ-002"
  ]
}
```

Do not add extra top-level or item-level fields.

## 5. DuplicateGroups Rules

Each `DuplicateGroups` item must:

1. contain at least two different supplied RequirementIds;
2. contain only requirements that express the same complete material
   obligation;
3. contain each RequirementId once;
4. preserve the original input order of RequirementIds;
5. include a concise `Reason`;
6. include a valid `CanonicalRequirement`.

Do not create a group from requirements that are merely related, share
keywords or belong to the same topic.

Do not merge requirements that differ materially in responsible party,
action, trigger, condition, exception, scope, outcome, timeframe, quantity,
threshold, standard, clause, service level, deliverable or legal effect.

## 6. UniqueRequirementIds Rules

`UniqueRequirementIds` must contain every supplied RequirementId that is not
part of a valid duplicate group.

Each unique RequirementId must appear once and must not also appear inside
`DuplicateGroups`.

## 7. CanonicalRequirement Rules

Every `CanonicalRequirement` must:

- be a non-empty, complete standalone sentence;
- identify the responsible party or subject;
- state the required action or obligation;
- preserve all material conditions, triggers, exceptions and outcomes;
- preserve mandatory strength and legal meaning;
- be supported by every RequirementId in the group;
- avoid invented wording or unsupported obligations;
- avoid combining different duties;
- prefer the clearest and most complete faithful source wording.

Invalid fragments include:

- `"will, if required, enter into an agreement..."`
- `"are properly briefed about the Assignment..."`
- `"perform the services with due care..."`

Valid forms include:

- `"The Supplier Staff will, if required, enter into a confidentiality agreement with Cadent."`
- `"The Supplier must ensure that Supplier Staff are properly briefed about their Assignment."`
- `"The Supplier must ensure that Temporary Workers perform their Assignment with due skill, care and diligence."`

Before returning the response, confirm that each CanonicalRequirement has a
subject, obligation, preserved trigger and complete standalone meaning.

## 8. Cross-Wording Duplicate Review

Compare meaning rather than exact wording.

Phrases such as the following may express the same trigger:

- `"if required"`
- `"at its request"`
- `"upon request"`
- `"when requested"`
- `"where required"`

They may be treated as equivalent only when the responsible party, action,
object, scope, condition and legal effect are also the same.

Do not keep requirements separate only because one uses `"will"` and another
uses `"must"`.

Do not merge when:

- the responsible party differs;
- one applies to the Supplier and another to Supplier Staff;
- one adds materially different agreement terms;
- one contains an additional legal condition;
- the trigger or outcome differs.

## 9. Strict RequirementId Coverage

Across `DuplicateGroups.RequirementIds` and `UniqueRequirementIds`:

- every supplied RequirementId must appear exactly once;
- no supplied RequirementId may be omitted;
- no RequirementId may be repeated;
- no unknown RequirementId may appear.

The complete input and output RequirementId sets must be identical.

## 10. Ordering

Return output groups according to the first appearance of their
RequirementIds in the input.

Preserve original input order within each `RequirementIds` array and within
`UniqueRequirementIds`.

## 11. Final Quality Review

Before returning the JSON:

1. Confirm every supplied RequirementId appears exactly once.
2. Confirm every duplicate group contains at least two RequirementIds.
3. Confirm materially different requirements remain separate.
4. Confirm semantically equivalent wording has been reviewed.
5. Confirm every CanonicalRequirement is complete and standalone.
6. Confirm no CanonicalRequirement adds unsupported information.
7. Confirm the response follows the required JSON schema exactly.

## 12. JSON Rules

1. Return one JSON object only.
2. Use double quotes for property names and string values.
3. Do not include trailing commas.
4. Do not return Markdown fences.
5. Do not return additional properties.
6. Ensure the response can be parsed directly by `json.loads()`.