Duplicate Removal Specification

Version: 1.3

1. Purpose

This Specification defines the runtime process, semantic comparison logic, runtime loading checks and post-processing validation required for duplicate removal.

The agent and host application must follow the Duplicate Removal Constitution.

The process must focus only on:

duplicate candidate matching;

actor resolution;

semantic comparison;

duplicate grouping;

final duplicate audit;

prompt-loading verification;

post-processing preservation;

duplicate summary validation.

Return one strict JSON object only.

2. Input Structure

Each input requirement should contain:

{
  "RequirementId": "REQ-001",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent.",
  "RequirementType": "Legal",
  "ParentText": "The Supplier must ensure that all Supplier Staff:",
  "LinkedContext": null
}

Input Rules

RequirementId must be preserved exactly.

RequirementText is the primary semantic source.

ParentText and LinkedContext may be used only when explicitly supplied.

RequirementType must not decide duplication.

IntentResult, capability intent, evidence sections and semantic anchors must not be used to prove duplication or resolve the actor.

3. Mandatory Pre-Deduplication Semantic Tagging Stage

Before duplicate candidate generation, the host application or a dedicated semantic-tagging step must enrich every requirement with structured semantic tags.

The deduplication LLM must receive the requirement and its tags together in the same object.

Required sequence:

1. Extract requirement
2. Attach parent or linked context
3. Generate semantic tags
4. Validate semantic tags
5. Send requirement plus tags to deduplication
6. Generate duplicate candidates
7. Compare complete semantic fields
8. Merge duplicate groups

3.1 Required Enriched Input Structure

{
  "RequirementId": "REQ-003",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "RequirementType": "Legal",
  "ParentText": "The Supplier must ensure that all Supplier Staff:",
  "LinkedContext": null,
  "SemanticTags": {
    "ResponsibleParty": [
      "Supplier Staff"
    ],
    "Action": [
      "enter into"
    ],
    "Object": [
      "confidentiality agreement"
    ],
    "Counterparty": [
      "Cadent"
    ],
    "Trigger": [
      "if required"
    ],
    "Timing": [],
    "Scope": [],
    "Conditions": [],
    "Exceptions": [],
    "Qualifiers": [
      "terms acceptable to Cadent",
      "form acceptable to Cadent"
    ]
  }
}

3.2 Required Semantic Tag Schema

{
  "ResponsibleParty": [],
  "Action": [],
  "Object": [],
  "Counterparty": [],
  "Trigger": [],
  "Timing": [],
  "Scope": [],
  "Conditions": [],
  "Exceptions": [],
  "Qualifiers": []
}

Rules:

every field is mandatory;

every field must be an array;

use an empty array when a value is unresolved;

do not use null for semantic-tag arrays;

preserve tags with their original requirement.

3.3 Tag Generation Logic

Generate tags from:

RequirementText
→ ParentText
→ LinkedContext

Priority for responsible-party resolution:

responsible_party = (
    extract_actor(RequirementText)
    or extract_actor(ParentText)
    or extract_actor(LinkedContext)
)

Do not resolve the actor from:

RequirementType
IntentResult
CapabilityIntent
EvidenceSections
generic SemanticAnchors
nearby unrelated requirements

3.4 Example: Fragment with Parent Context

Input before tagging:

{
  "RequirementId": "REQ-003",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent.",
  "ParentText": "The Supplier must ensure that all Supplier Staff:"
}

Output from the semantic-tagging stage:

{
  "RequirementId": "REQ-003",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent.",
  "ParentText": "The Supplier must ensure that all Supplier Staff:",
  "SemanticTags": {
    "ResponsibleParty": [
      "Supplier Staff"
    ],
    "Action": [
      "enter into"
    ],
    "Object": [
      "confidentiality agreement"
    ],
    "Counterparty": [
      "Cadent"
    ],
    "Trigger": [
      "if required"
    ],
    "Timing": [],
    "Scope": [],
    "Conditions": [],
    "Exceptions": [],
    "Qualifiers": []
  }
}

3.5 Example: Complete Requirement

{
  "RequirementId": "REQ-009",
  "RequirementText": "The Supplier Staff must enter into a direct confidentiality agreement with Cadent at its request.",
  "SemanticTags": {
    "ResponsibleParty": [
      "Supplier Staff"
    ],
    "Action": [
      "enter into"
    ],
    "Object": [
      "confidentiality agreement"
    ],
    "Counterparty": [
      "Cadent"
    ],
    "Trigger": [
      "at its request"
    ],
    "Timing": [],
    "Scope": [],
    "Conditions": [],
    "Exceptions": [],
    "Qualifiers": [
      "direct"
    ]
  }
}

3.6 Required Duplicate Comparison Using Tags

The deduplication stage must compare:

ResponsibleParty
Action
Object
Counterparty
Trigger
Timing
Scope
Conditions
Exceptions
Qualifiers

For the two examples above:

Semantic field

REQ-003

REQ-009

Result

ResponsibleParty

Supplier Staff

Supplier Staff

Same

Action

enter into

enter into

Same

Object

confidentiality agreement

confidentiality agreement

Same

Counterparty

Cadent

Cadent

Same

Trigger

if required

at its request

Equivalent

Qualifiers

acceptable terms/form

direct

Compatible

Required decision:

SemanticDuplicate

3.7 Required Merged Output

{
  "CanonicalRequirementId": "CR-0007",
  "CanonicalRequirement": "The Supplier Staff must, at Cadent's request, enter into a direct confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "RequirementIds": [
    "REQ-003",
    "REQ-009"
  ],
  "RequirementType": "Legal"
}

3.8 Generic Semantic Anchors Must Not Replace Structured Tags

This is not sufficient:

"SemanticAnchors": [
  "confidentiality agreement",
  "Cadent",
  "terms",
  "form",
  "supplier staff"
]

Reason:

supplier staff is not explicitly labelled as the responsible party;

Cadent is not explicitly labelled as the counterparty;

terms and form are not identified as qualifiers;

duplicate comparison cannot reliably understand the role of each value.

Structured SemanticTags are mandatory before deduplication.

3.9 Pre-Deduplication Validation

Before candidate matching, validate every requirement:

SemanticTags exists
All required fields exist
All fields are arrays
Tags belong to the same requirement
ResponsibleParty was resolved from valid source context
No unsupported tags were added

When validation fails, return:

{
  "ValidationError": {
    "Code": "SEMANTIC_TAGGING_FAILED",
    "Message": "Structured semantic tags could not be generated or validated before duplicate comparison.",
    "AffectedRequirementIds": [
      "REQ-003"
    ],
    "MissingRequirementIds": [],
    "RepeatedRequirementIds": [],
    "UnknownRequirementIds": []
  }
}

The deduplication stage must not continue with incomplete or invalid structured tags.

4. Required Runtime Process

Step 1: Verify Prompt Files

Before processing requirements, the host application must verify that the current Constitution and Specification are loaded.

Required checks:

Constitution file exists
Specification file exists
Constitution version = 1.1
Specification version = 1.1
Constitution content is non-empty
Specification content is non-empty
Both contents are present in the final LLM prompt

The host application should log:

Constitution path
Specification path
Constitution version
Specification version
Constitution hash
Specification hash
Final prompt length

If any check fails, return:

{
  "ValidationError": {
    "Code": "PROMPT_LOADING_FAILED",
    "Message": "The current duplicate-removal Constitution or Specification was not loaded into the final LLM prompt.",
    "AffectedRequirementIds": [],
    "MissingRequirementIds": [],
    "RepeatedRequirementIds": [],
    "UnknownRequirementIds": []
  }
}

Step 2: Validate Input IDs

Create the ordered list of distinct supplied IDs.

Reject:

empty IDs;

duplicate input IDs;

malformed requirements.

Step 3: Resolve Actors

Resolve the responsible party from:

RequirementText;

ParentText;

LinkedContext;

inseparable list context.

Example input:

{
  "RequirementId": "REQ-003",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent.",
  "ParentText": "The Supplier must ensure that all Supplier Staff:"
}

Resolved internal requirement:

Actor: Supplier Staff
Action: enter into
Object: confidentiality agreement
Counterparty: Cadent
Trigger: if required

When the actor cannot be resolved, classify related duplicate candidates as UnresolvedDuplicate.

Step 4: Normalise Candidate Phrases

Normalise phrases before candidate generation.

Minimum trigger normalisation:

{
  "if required": "on_request",
  "when requested": "on_request",
  "upon request": "on_request",
  "at its request": "on_request",
  "at cadent's request": "on_request"
}

Minimum action normalisation:

{
  "enter into": "execute_agreement",
  "execute": "execute_agreement",
  "sign": "execute_agreement"
}

Minimum modality normalisation:

{
  "must": "mandatory",
  "shall": "mandatory",
  "will": "mandatory_when_contractual"
}

Normalisation is used only for comparison. It must not overwrite source text.

Step 5: Generate Duplicate Candidates

Generate a duplicate candidate when requirements share compatible values for:

actor;

normalised action;

action object;

counterparty;

normalised trigger.

Do not require high lexical similarity when these semantic fields match.

Example candidate pair:

CR candidate A:
will, if required, enter into a confidentiality agreement with Cadent.

CR candidate B:
The Supplier Staff must enter into a direct confidentiality agreement with Cadent at its request.

When parent context resolves candidate A to Supplier Staff, the pair must proceed to semantic comparison.

Step 6: Build Full Obligation Signature

For every requirement, derive internally:

ResponsibleParty;

Modality;

Negation;

Action;

ActionObject;

CounterpartyOrBeneficiary;

Trigger;

Timing;

Scope;

Conditions;

Exceptions;

LegalEffect.

Do not return these fields.

Step 7: Perform Semantic Comparison

Compare each candidate using the full obligation signature.

Classification options:

ExactDuplicate;

SemanticDuplicate;

NotDuplicate;

UnresolvedDuplicate.

Classify as SemanticDuplicate when:

actors match;

actions are equivalent;

objects match;

counterparties match;

triggers are equivalent;

no timing, scope, condition, exception or legal-effect conflict exists;

one canonical requirement can preserve both meanings.

Example:

Field

Requirement A

Requirement B

Result

Actor

Supplier Staff

Supplier Staff

Same

Action

Enter into

Execute

Equivalent

Object

Confidentiality agreement

Direct confidentiality agreement

Compatible

Counterparty

Cadent

Cadent

Same

Trigger

If required

At its request

Equivalent

Final decision





SemanticDuplicate

Step 8: Build Duplicate Groups

For every exact or semantic duplicate group:

include all matching source IDs;

include each ID once;

create one canonical requirement;

preserve compatible details.

Correct group example:

{
  "CanonicalRequirementId": "CR-0007",
  "CanonicalRequirement": "The Supplier Staff must, at Cadent's request, enter into a direct confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "RequirementIds": [
    "REQ-003",
    "REQ-009"
  ],
  "RequirementType": "Legal"
}

Step 9: Final Pairwise Duplicate Audit

After generating final records, compare every final canonical requirement against every other final canonical requirement.

Pseudo-process:

repeat
    duplicate_found = false

    for each final record A
        for each final record B after A
            compare full obligation signatures

            if A and B are duplicates
                merge A and B
                regenerate canonical wording
                duplicate_found = true

until duplicate_found = false

The response must not be returned before this loop is stable.

Step 10: Capture Raw LLM Output

The host application must log the raw LLM response before:

JSON parsing;

enrichment;

canonical text replacement;

MongoDB mapping.

Required log label:

DEDUPLICATION_RAW_LLM_OUTPUT

Step 11: Protect Groups During Post-Processing

Post-processing must preserve:

canonical grouping;

all grouped requirement IDs;

canonical record count;

canonical wording unless only safe formatting is applied.

The application must compare these stages:

Raw LLM output
Parsed output
Enriched output
MongoDB payload

For every stage, calculate a group signature:

sorted RequirementIds joined together

Example:

REQ-003|REQ-009

The same signature must exist in every stage.

If raw output contains:

"RequirementIds": ["REQ-003", "REQ-009"]

but MongoDB contains two separate records, return:

{
  "ValidationError": {
    "Code": "POST_PROCESSING_GROUP_CHANGED",
    "Message": "A valid duplicate group returned by the LLM was changed during parsing, enrichment or persistence.",
    "AffectedRequirementIds": [
      "REQ-003",
      "REQ-009"
    ],
    "MissingRequirementIds": [],
    "RepeatedRequirementIds": [],
    "UnknownRequirementIds": []
  }
}

Step 12: Validate ID Coverage

Confirm:

every input ID appears once;

no ID is missing;

no ID is repeated;

no unknown ID is added.

Step 13: Calculate Summary

Calculate:

TotalInputRequirements =
number of distinct input RequirementIds

TotalDeduplicatedRequirements =
number of final canonical records

DuplicatesRemoved =
TotalInputRequirements - TotalDeduplicatedRequirements

5. Mandatory Confidentiality Example

Input A

{
  "RequirementId": "REQ-003",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "ParentText": "The Supplier must ensure that all Supplier Staff:"
}

Input B

{
  "RequirementId": "REQ-009",
  "RequirementText": "The Supplier Staff must enter into a direct confidentiality agreement with Cadent at its request.",
  "ParentText": null
}

Resolved comparison

Actor A = Supplier Staff
Actor B = Supplier Staff

Action A = execute_agreement
Action B = execute_agreement

Object A = confidentiality agreement
Object B = direct confidentiality agreement

Counterparty A = Cadent
Counterparty B = Cadent

Trigger A = on_request
Trigger B = on_request

Required decision

SemanticDuplicate

Required merged output

{
  "CanonicalRequirementId": "CR-0007",
  "CanonicalRequirement": "The Supplier Staff must, at Cadent's request, enter into a direct confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "RequirementIds": [
    "REQ-003",
    "REQ-009"
  ],
  "RequirementType": "Legal"
}

6. Non-Duplicate Examples

Do not merge:

The Supplier Staff must sign a confidentiality agreement.

with:

The Supplier must maintain a confidentiality policy.

Reason:

Different actor
Different action
Different required output

Do not merge:

The Supplier must train staff on confidentiality.

with:

Supplier Staff must sign confidentiality agreements.

Reason:

Training obligation is different from agreement execution.

7. Successful Output Schema

Return exactly:

{
  "Summary": {
    "TotalInputRequirements": 10,
    "TotalDeduplicatedRequirements": 8,
    "DuplicatesRemoved": 2
  },
  "JsonOutput": {
    "DeduplicatedRequirements": [
      {
        "CanonicalRequirementId": "CR-0001",
        "CanonicalRequirement": "The Supplier must perform the specified obligation.",
        "RequirementIds": [
          "REQ-001"
        ],
        "RequirementType": "Compliance"
      }
    ]
  }
}

8. Validation Error Schema

Return exactly:

{
  "ValidationError": {
    "Code": "UNRESOLVED_DUPLICATE",
    "Message": "A potential semantic duplicate could not be resolved from the supplied requirement text or linked context.",
    "AffectedRequirementIds": [
      "REQ-001",
      "REQ-002"
    ],
    "MissingRequirementIds": [],
    "RepeatedRequirementIds": [],
    "UnknownRequirementIds": []
  }
}

Permitted error codes:

PROMPT_LOADING_FAILED;

SEMANTIC_TAGGING_FAILED;

INVALID_INPUT_IDS;

UNRESOLVED_DUPLICATE;

INVALID_DUPLICATE_GROUP;

DUPLICATE_REMAINS;

POST_PROCESSING_GROUP_CHANGED;

REQUIREMENT_ID_COVERAGE_FAILED;

DUPLICATE_SUMMARY_FAILED;

OUTPUT_SCHEMA_VALIDATION_FAILED.

Do not return partial success.

9. Final Duplicate Removal Checklist

Before returning success, confirm:

current Constitution and Specification were loaded;

equivalent phrases were normalised;

actors were resolved from valid context;

candidate matching used semantic fields;

full obligation signatures were compared;

all supported semantic duplicates were merged;

no duplicate remains after the final audit;

raw LLM groups were preserved through post-processing;

each input ID appears exactly once;

summary values match the final output.

If any check fails, return the appropriate validation error.

Mandatory Runtime Test: Confidentiality Fragment Duplicate

The runtime must explicitly handle the following test case.

Input A

{
  "RequirementId": "REQ-A",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "RequirementType": "Legal",
  "ParentText": "The Supplier must ensure that all Supplier Staff:",
  "LinkedContext": null,
  "SemanticTags": {
    "ResponsibleParty": ["Supplier Staff"],
    "Action": ["enter into"],
    "Object": ["confidentiality agreement"],
    "Counterparty": ["Cadent"],
    "Trigger": ["if required"],
    "Timing": [],
    "Scope": [],
    "Conditions": [],
    "Exceptions": [],
    "Qualifiers": [
      "terms acceptable to Cadent",
      "form acceptable to Cadent"
    ]
  }
}

Input B

{
  "RequirementId": "REQ-B",
  "RequirementText": "The Supplier Staff must enter into a direct confidentiality agreement with Cadent at its request.",
  "RequirementType": "Compliance",
  "ParentText": null,
  "LinkedContext": null,
  "SemanticTags": {
    "ResponsibleParty": ["Supplier Staff"],
    "Action": ["enter into"],
    "Object": ["confidentiality agreement"],
    "Counterparty": ["Cadent"],
    "Trigger": ["at its request"],
    "Timing": [],
    "Scope": [],
    "Conditions": [],
    "Exceptions": [],
    "Qualifiers": ["direct"]
  }
}

Required normalization

if required        → on_request
at its request     → on_request
enter into         → execute_agreement
must               → mandatory
contractual will   → mandatory

Required comparison result

ResponsibleParty: Supplier Staff = Supplier Staff
Action: execute_agreement = execute_agreement
Object: confidentiality agreement = confidentiality agreement
Counterparty: Cadent = Cadent
Trigger: on_request = on_request
Qualifiers: compatible

Required decision:

SemanticDuplicate

Required merged output

{
  "CanonicalRequirementId": "CR-0001",
  "CanonicalRequirement": "The Supplier Staff must, at Cadent's request, enter into a direct confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "RequirementIds": [
    "REQ-A",
    "REQ-B"
  ],
  "RequirementType": "Legal"
}

Prohibited result

It is invalid to return Requirement A and Requirement B as two separate canonical records after valid actor resolution.

Unresolved actor behavior

If Requirement A does not include valid ParentText, LinkedContext, or SemanticTags.ResponsibleParty, return:

{
  "ValidationError": {
    "Code": "UNRESOLVED_DUPLICATE",
    "Message": "The responsible party for a potential confidentiality-agreement duplicate could not be resolved safely.",
    "AffectedRequirementIds": [
      "REQ-A",
      "REQ-B"
    ],
    "MissingRequirementIds": [],
    "RepeatedRequirementIds": [],
    "UnknownRequirementIds": []
  }
}

The runtime must never silently keep the pair separate when the pre-deduplication stage should have supplied the missing actor.