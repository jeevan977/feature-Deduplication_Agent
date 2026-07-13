# User Prompt – Requirement Deduplication Agent

## INPUTS

The AI agent will receive:

1. Constitution File
2. Specification File
3. Raw Requirement JSON

## TASK

Analyse the supplied raw requirements.

Determine:

- duplicates
- semantic equivalence
- repeated obligations
- repeated supplier expectations

If duplicates exist:

Create canonical requirements.

Follow:

- Constitution File
- Specification File

## IMPORTANT RULES

- preserve meaning
- do not hallucinate
- preserve strongest wording
- preserve source lineage
- do not merge unrelated requirements
- output must follow specification schema

## INPUT EXAMPLE

[
  {
    "RequirementId":"REQ001",
    "RequirementText":"Supplier must hold ISO27001"
  },
  {
    "RequirementId":"REQ044",
    "RequirementText":"Supplier shall maintain ISO27001 certification"
  }
]

Return only Specification-compliant JSON.
