# PROMPT_ENGINE_v2.md

## Purpose

PROMPT_ENGINE_v2 is the governed default system for prompt design and prompt improvement.
It upgrades the earlier prompt system by making prompt work:

- artifact-aware
- task-aware
- model/tool/environment-aware
- research-aware
- validation-aware
- failure-aware
- next-command-aware
- safely self-improving

This engine is meant to be used whenever a prompt is created, revised, hardened, or audited.

---

## Core Principles

1. **Artifacts over memory**
   - If authoritative artifacts exist, prompts must be shaped from them.
   - Do not prefer recollection over available runtime/project artifacts.

2. **Task-model-tool-environment fit**
   - Prompts must be adapted to the actual target:
     - ChatGPT chat
     - ChatGPT with tools
     - Claude Code
     - Codex
     - Termux / Android shell
     - repo/build workflow
     - debugging workflow
     - research workflow

3. **Research when current facts matter**
   - If the prompt depends on current methods, current platform behavior, current product behavior, or external evidence, web.run is mandatory.

4. **Success criteria before wording polish**
   - A prompt is not good because it sounds good.
   - A prompt is good if it defines success clearly enough that the downstream system can execute and be judged.

5. **Fail-closed where correctness matters**
   - Prompts should require explicit checks, artifact outputs, and validation when the task is build, repair, analysis, export, or research-heavy work.

6. **No vague next steps**
   - Every operational prompt should force the downstream response to end with the next correct command or ranked next options.

7. **Safe self-improvement**
   - The engine should improve from evidenced weaknesses, not from vibes or one-off frustration.
   - Record weakness first.
   - Patch engine or profile only when the weakness is reusable.

---

## Stage Flow

### Stage 1 — Task Classification

Classify the prompt target:

- writing / transformation
- research / synthesis
- coding / implementation
- debugging / repair
- artifact audit / consolidation
- workflow / SOP design
- repo / setup / environment
- extraction / parsing / normalization
- teaching / lesson / assessment build

Required output:
- task type
- task objective
- main risk if misprompted

---

### Stage 2 — Environment / Tool / Model Classification

Lock the downstream environment:

- target model/system
- available tools
- runtime environment
- artifact context
- OS or platform constraints
- execution vs planning vs auditing mode

Examples:
- ChatGPT with web.run
- Claude Code repo editing
- Codex plan mode
- Termux on Android
- Windows PowerShell local execution

Required output:
- environment profile
- tool assumptions
- blocked assumptions

---

### Stage 3 — Authority / Artifact Lock

Identify what governs the task:

- attached files
- project artifacts
- runtime artifacts
- SOPs
- manifests
- receipts
- user-provided instructions
- external official sources if current evidence is needed

Rules:
- Earlier authority layers override later ones if explicitly stated.
- Do not let the prompt drift away from the authoritative source set.

Required output:
- authority list
- precedence order
- missing authority inputs, if any

---

### Stage 3.5 — Success Criteria + Eval Shape

Before finalizing the prompt, define:

- what success looks like
- what failure looks like
- what evidence proves success
- what validators or checks are required
- whether artifacts, citations, tests, or readbacks are needed

Rules:
- Success criteria must be concrete enough to reject shallow completion.
- If the task is build/repair/research-heavy, the prompt should define how correctness will be checked.

Required output:
- success criteria
- validation/eval shape
- fail conditions

---

### Stage 4 — Research Requirement Decision

Determine whether current external research is required.

Research is mandatory when:
- the user explicitly asks for it
- the task depends on current methods or current platform behavior
- the prompt must be evidence-backed
- recommendations could have changed
- the task involves current products, APIs, libraries, tooling, or workflow methods

If research is required:
- use web.run
- prefer primary and official sources
- require SEE and CE for planning and processing

Required output:
- research required? yes/no
- if yes, what must be researched
- preferred source types

---

### Stage 4.5 — Prompt Profile Selection

Select the correct prompt profile.

Supported profiles include:
- ChatGPT research prompt
- ChatGPT coding/build prompt
- ChatGPT artifact-audit prompt
- Claude Code implementation prompt
- Codex repair/build prompt
- Termux / Android setup prompt
- debugging-engine prompt
- workflow/SOP prompt
- document/PDF extraction prompt

Rules:
- Every serious prompt must explicitly fit its target profile.
- Do not reuse a coding-heavy prompt shape for a research-only task or vice versa.

Required output:
- profile selected
- why it fits
- special constraints for that profile

---

### Stage 5 — Failure-Mode Modeling

Model the likely prompt failures before drafting.

Common failure classes:
- skipped research
- skipped authority load
- environment mismatch
- scope drift
- fake completeness
- weak validation
- overclaiming
- shallow summary instead of execution plan
- wrong artifact target
- no next-step guidance
- generic instead of tool-aware output
- missing distinction between options

Required output:
- top expected failure modes
- counter-rules to block them

---

### Stage 6 — Prompt Drafting

Write the prompt.

The draft must include, when relevant:
- authoritative baseline
- non-negotiable rules
- required workflow
- required output order
- validation requirements
- special requirements
- final instruction

Rules:
- Prompts should be explicit, structured, and operational.
- Use direct language.
- Prefer governed stage structure over loose prose for complex tasks.

---

### Stage 6.5 — Next-Step Output Rules

Every operational prompt must end with either:

#### A. Next Correct Command
Use this when exactly one next step is the best move.

Format:
- heading: `Next Correct Command`
- one short sentence explaining why this is the right next move
- one copyable code block containing only the command

#### B. Ranked Next Options
Use this when more than one next step is valid.

Format:
- heading: `Ranked Next Options`
- for each option, include in this exact order:
  1. option label
  2. `Use this when:` followed by the situation/decision condition
  3. `Why choose this:` followed by how it differs from the other options
  4. one separate copyable code block containing only that option’s command

Hard rules:
- the explanation for each option must appear in the same response
- the explanation must appear directly adjacent to that option’s command block
- do not defer explanation to a later turn
- do not group multiple commands into one code block
- do not end with vague language like `proceed when ready`
- if there is one best next move, do not output multiple options
- if there are multiple real options, rank them from strongest/default to weakest/situational

---

### Stage 7 — Weakness Capture / Governed Self-Improvement

After a prompt is used, capture reusable weaknesses.

Record:
- what failed
- where it failed
- whether the failure was due to:
  - missing authority
  - skipped research
  - weak validation
  - wrong profile
  - wrong environment assumptions
  - weak success criteria
  - weak next-step formatting
  - missing failure-mode blocking

Rules:
- do not auto-patch the engine from one weak outcome unless the weakness is clearly reusable
- separate core-engine weaknesses from profile-specific weaknesses
- preserve changelog and rationale

Required output:
- weakness classification
- fix candidate
- patch target:
  - core engine
  - prompt profile
  - task-specific one-off

---

## Required Prompt Components

For serious prompts, include all applicable components:

1. Primary goal
2. Authoritative baseline
3. Non-negotiable rules
4. Required workflow
5. Required output order
6. Special requirements
7. Validation / failure gates
8. Next-step output requirement

---

## Prompt Profiles

### 1. Research Prompt
Use when the downstream chat must gather and process external evidence.
Must include:
- web.run requirement
- SEE + CE requirement
- source priority
- explicit research questions
- separation of validated claims vs inference

### 2. Coding / Build Prompt
Use when the downstream chat must design, implement, patch, or wire code.
Must include:
- artifact authority
- exact build target
- staged workflow
- validation requirements
- fail-closed conditions
- implementation boundaries

### 3. Artifact Audit Prompt
Use when the task is analyzing files, bundles, manifests, receipts, or runtime state.
Must include:
- inventory step
- lineage/readback verification
- redundancy/supersession analysis
- authority determination
- consolidation or repair plan

### 4. Debugging Prompt
Use when the task is repair, diagnosis, or regression handling.
Must include:
- reproduce/classify/isolate/instrument/patch/verify loop
- smallest valid patch rule
- regression checks
- writeback of reusable failure lessons

### 5. Workflow / SOP Prompt
Use when the task is governance design or SOP updates.
Must include:
- evidence base
- generalization test
- gap analysis
- proposed additions with failure modes prevented
- priority and placement

### 6. Environment / Setup Prompt
Use when the task involves repo setup, Termux, PowerShell, Android, or local execution.
Must include:
- environment-specific constraints
- dependency/tool checks
- path/workspace rules
- user-effort reduction plan
- resume/retry strategy if relevant

---

## Failure Classes

Standard failure classes for prompt review:

- FC01 skipped authority
- FC02 skipped current research
- FC03 wrong tool/environment assumptions
- FC04 vague success criteria
- FC05 weak validation
- FC06 scope drift
- FC07 fake completeness
- FC08 overclaiming
- FC09 wrong artifact target
- FC10 no governed stage flow
- FC11 no actionable next step
- FC12 multiple options not distinguished
- FC13 prompt not profile-fit
- FC14 missing fail-closed conditions

---

## Output Standard for Prompt Improvements

When asked to improve a prompt, default to this response shape:

1. `Use this prompt:`
2. one clean copyable prompt block
3. short explanation of why it is stronger
4. next-step block using Stage 6.5 rules

If the user asks for only the artifact/download, provide the artifact directly.

---

## Self-Improvement Safety Rule

PROMPT_ENGINE_v2 may improve itself only through this sequence:

1. weakness observed
2. weakness recorded
3. weakness classified
4. reusable or not decided
5. patch proposed
6. patch applied to:
   - core engine only if broadly reusable
   - profile if environment/model-specific
   - one-off prompt if local only
7. changelog updated

No silent self-rewrites.

---

## Default Rule Going Forward

Whenever the user asks to improve a prompt:

- load this engine
- classify the task
- classify the environment/model/tool
- decide whether research is required
- lock authority
- define success criteria
- pick the correct prompt profile
- model likely failures
- draft the prompt
- enforce next-step output rules
- capture reusable weaknesses afterward if needed
