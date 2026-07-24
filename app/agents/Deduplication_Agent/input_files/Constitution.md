Duplicate Removal Constitution

Version: 1.3

1. Purpose

The Deduplication Agent must identify and merge all exact and semantic duplicate requirements.

The agent must focus only on duplicate removal and must not target a predefined duplicate count.

A duplicate decision must be based on the full obligation, not only on similar wording.

2. Duplicate Definition

Two requirements are duplicates when they express the same material obligation and satisfying one would substantially satisfy the other.

The comparison must consider:

responsible party;

action;

action object;

counterparty or beneficiary;

trigger;

timing;

scope;

conditions;

exceptions;

obligation strength;

legal or operational effect.

3. Mandatory Pre-Deduplication Semantic Tagging

Before duplicate candidate generation, every requirement must be enriched with structured semantic tags.

The semantic-tagging stage must run before deduplication.

Required processing order:

Requirement extraction
        ↓
Resolve source and parent context
        ↓
Generate structured semantic tags
        ↓
Attach tags to the same requirement
        ↓
Run duplicate candidate matching
        ↓
Run semantic duplicate comparison
        ↓
Create final duplicate groups

Every requirement must carry its own semantic tags.

Required structure:

{
  "RequirementId": "REQ-003",
  "RequirementText": "will, if required, enter into a confidentiality agreement with Cadent.",
  "RequirementType": "Legal",
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
    "Qualifiers": [
      "terms acceptable to Cadent",
      "form acceptable to Cadent"
    ]
  }
}

3.1 Tag Ownership

Semantic tags must remain attached to the requirement from which they were derived.

Do not:

create one shared tag collection for all requirements;

move tags from one requirement to another;

infer that a tag applies to another requirement because the wording is similar;

use tags belonging to one source requirement as direct evidence for an unrelated requirement.

3.2 Required Semantic Tag Fields

Each requirement must contain:

ResponsibleParty;

Action;

Object;

Counterparty;

Trigger;

Timing;

Scope;

Conditions;

Exceptions;

Qualifiers.

Each field must be an array.

Use an empty array when the value cannot be established safely.

3.3 Semantic Tag Generation Sources

Tags may be generated only from:

RequirementText;

explicit ParentText;

explicit LinkedContext;

inseparable source-clause or list context.

Tags must not be generated from:

another unrelated requirement;

RequirementType alone;

existing IntentResult;

capability-intent classification;

evidence-routing output;

general tender knowledge.

3.4 Responsible-Party Tag Rule

When the responsible party is explicit in the text, copy it into:

"ResponsibleParty": ["Supplier Staff"]

When the requirement is a fragment, resolve the actor from valid parent or linked context before deduplication.

Example:

ParentText:
The Supplier must ensure that all Supplier Staff:

RequirementText:
will, if required, enter into a confidentiality agreement with Cadent.

Required semantic tag:

"ResponsibleParty": ["Supplier Staff"]

When the actor cannot be resolved safely:

"ResponsibleParty": []

The deduplication stage must then classify any actor-dependent comparison as unresolved rather than guessing.

3.5 Structured Tags Instead of Generic Semantic Anchors

A generic list such as:

"SemanticAnchors": [
  "confidentiality agreement",
  "Cadent",
  "terms",
  "form",
  "supplier staff"
]

is insufficient for duplicate comparison because the role of each value is unclear.

The deduplication stage must use structured tags:

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

3.6 Pre-Deduplication Tag Validation

Before duplicate matching starts, validate that:

every requirement has a SemanticTags object;

every required semantic field exists;

every field is an array;

tags are attached to the correct requirement;

the responsible party is resolved when valid source context is available;

no tag was invented from unsupported information.

If the semantic-tagging stage fails, duplicate comparison must not begin.

Return a validation error instead.

4. Required Duplicate-Removal Capabilities

3.1 Candidate Matching

The agent must create duplicate candidates using semantic equivalence, not only lexical similarity.

Equivalent phrases must be normalised before comparison.

Examples:

Source phrase

Normalised meaning

if required

on request

when requested

on request

upon request

on request

at its request

on request

at Cadent's request

on request

enter into an agreement

execute agreement

sign an agreement

execute agreement

execute an agreement

execute agreement

Example duplicate candidates:

will, if required, enter into a confidentiality agreement with Cadent; and

must enter into a direct confidentiality agreement with Cadent at its request.

These must be treated as duplicate candidates because their action, object, counterparty and trigger are semantically equivalent.

3.2 Actor Resolution

The responsible party must be identified before a final duplicate decision.

The agent may resolve the actor only from:

the requirement text;

explicit parent text;

explicit linked context;

an inseparable list heading;

another requirement already proven to be part of the same source clause.

The agent must not infer the actor from:

RequirementType;

IntentResult;

capability intent;

semantic anchors;

evidence sections;

nearby unrelated requirements;

general tender knowledge.

Example:

ParentText:
The Supplier must ensure that all Supplier Staff:

RequirementText:
will, if required, enter into a confidentiality agreement with Cadent.

Resolved meaning:

The Supplier Staff must, if required, enter into a confidentiality agreement with Cadent.

When parent or linked context is not supplied, the agent must mark the duplicate decision unresolved instead of guessing.

3.3 Semantic Comparison

The agent must compare the full obligation signature:

Actor + Action + Object + Counterparty + Trigger
+ Timing + Scope + Conditions + Exceptions + Legal Effect

The agent must not compare only raw text similarity.

Example:

Requirement A:

The Supplier Staff will, if required, enter into a confidentiality agreement with Cadent.

Requirement B:

The Supplier Staff must execute a direct confidentiality agreement with Cadent at its request.

Comparison:

Field

Requirement A

Requirement B

Decision

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

Result





Semantic duplicate

The requirements must be merged.

3.4 Final Duplicate Audit

After initial duplicate groups are created, every final canonical requirement must be compared against every other final canonical requirement.

If two final records still express the same obligation:

merge their groups;

combine all source IDs;

regenerate the canonical requirement;

rerun the audit.

The response must not be returned until no exact or semantic duplicate remains.

3.5 Runtime Prompt Loading

The application must ensure that the current Constitution and Specification are included in the exact prompt sent to the LLM.

The application must:

load the configured current file paths;

avoid stale cached prompt content;

log the loaded document names and versions;

log a hash or checksum of each loaded file;

log the final assembled prompt before the LLM call in a safe debug environment;

fail the run when the required files are missing or empty.

Example runtime log:

Deduplication constitution loaded: Duplicate_Removal_Constitution_v1.1.md
Deduplication specification loaded: Duplicate_Removal_Specification_v1.1.md
Constitution hash: <hash>
Specification hash: <hash>
Final prompt contains both documents: true

3.6 Post-Processing Protection

The application must preserve the duplicate groups returned by the LLM.

Post-processing must not:

split a valid multi-ID group;

replace canonical wording with the original requirement text;

regroup records using only lexical similarity;

remove requirement IDs from a duplicate group;

create a second canonical record for an already grouped obligation.

The application must log:

raw LLM output;

parsed deduplication output;

enriched output;

final MongoDB payload.

These outputs must be compared to confirm that duplicate groups remain unchanged.

Example:

Raw LLM group:
RequirementIds = [REQ-003, REQ-009]

Final MongoDB group:
RequirementIds = [REQ-003, REQ-009]

Group preserved: true

If the group changes between stages, the run must fail with a post-processing validation error.

5. Confidentiality-Agreement Duplicate Rule

Requirements must be treated as duplicate candidates when they express:

the same responsible party;

the duty to enter into, execute or sign a confidentiality agreement;

the same counterparty;

the same or equivalent request trigger.

Example:

Requirement A:

The Supplier Staff will, if required, enter into a confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.

Requirement B:

The Supplier Staff must enter into a direct confidentiality agreement with Cadent at its request.

Correct merged canonical requirement:

The Supplier Staff must, at Cadent's request, enter into a direct confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.

Compatible details such as direct, acceptable terms and acceptable form must be preserved when they do not create a separate obligation.

6. Requirements That Must Remain Separate

Do not merge requirements when they differ materially in:

responsible party;

action;

object or deliverable;

counterparty;

trigger;

timing;

scope;

condition;

exception;

modality;

legal effect.

These are not automatically duplicates:

sign a confidentiality agreement;

comply with a confidentiality policy;

protect confidential information;

train staff on confidentiality.

7. Duplicate Group Rules

For every duplicate group:

include every duplicate source RequirementId;

include each source ID exactly once;

produce one canonical requirement;

preserve compatible material details;

do not include unrelated requirements;

do not split the group later.

8. Summary Rule

Calculate:

DuplicatesRemoved =
TotalInputRequirements - TotalDeduplicatedRequirements

Do not hard-code an expected duplicate count.

9. Failure Conditions

Duplicate Removal fails when:

a supported semantic duplicate remains separate;

actor resolution was skipped;

candidate matching ignored equivalent phrases;

only lexical similarity was used;

the final duplicate audit was not completed;

stale prompt files were loaded;

post-processing changed an LLM duplicate group;

requirement IDs are missing, repeated or added;

summary values do not match the final groups.

Return JSON only.

Mandatory Example: Fragment and Complete Confidentiality Requirements

The following two requirements must be treated as semantic-duplicate candidates:

Requirement A

will, if required, enter into a confidentiality agreement with Cadent
on terms and in a form acceptable to Cadent.

Requirement B

The Supplier Staff must enter into a direct confidentiality agreement
with Cadent at its request.

Requirement A is a fragment because the responsible party is not visible in the text. Before deduplication, its actor must be resolved from its own ParentText, LinkedContext, source-clause context, or structured SemanticTags.

When valid context establishes that Requirement A applies to Supplier Staff, interpret the pair as follows:

Semantic field

Requirement A

Requirement B

Decision

Responsible party

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

acceptable terms and form

direct

Compatible

Required classification:

SemanticDuplicate

The agent must not keep these requirements separate merely because:

one requirement is a fragment;

one uses will and the other uses must;

one says if required and the other says at its request;

one contains direct;

one contains terms and form acceptable to Cadent;

their RequirementType values differ.

Required merged canonical requirement:

The Supplier Staff must, at Cadent's request, enter into a direct
confidentiality agreement with Cadent on terms and in a form acceptable
to Cadent.

Required merged structure:

{
  "CanonicalRequirementId": "CR-XXXX",
  "CanonicalRequirement": "The Supplier Staff must, at Cadent's request, enter into a direct confidentiality agreement with Cadent on terms and in a form acceptable to Cadent.",
  "RequirementIds": [
    "<RequirementId from Requirement A>",
    "<RequirementId from Requirement B>"
  ],
  "RequirementType": "Legal"
}

Merge this pair only when valid context or structured tags establish that Requirement A applies to Supplier Staff.

If the actor cannot be resolved safely, return UNRESOLVED_DUPLICATE instead of guessing or silently keeping the pair separate.

Apply this same reasoning to any future pair with equivalent actors, actions, agreement objects, counterparties and request-based triggers.