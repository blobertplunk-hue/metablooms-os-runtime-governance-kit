# MB_S-Tier_LLM_Workflow_System_v1

## Overview
This document defines a full S-tier LLM workflow system built for ChatGPT UI execution.

---

## Core Loop
INPUT → PREFLIGHT → SELECT → EXECUTE → VALIDATE → LEDGER → CONTINUITY → NEXT

---

## Preflight System
- CE (Context Engine)
- Task Decomposition
- Classification
- Cartridge Selection
- Stage Planning (MPP)
- Artifact Contracts
- Risk Analysis
- GO / NO-GO

---

## Orchestrator
- Selects next stage
- Selects cartridge
- Routes tool (ChatGPT / Canva / Scripts)
- Enforces one-stage-per-turn
- Manages handoffs

---

## Cartridge System
Types:
- Core: CE_Context_Packer, Spec_Planner, Verification_Critic
- Routing: Tool_Router, Platform_Router
- Build: Prompt_Generator, HTML_Builder
- Product: Canva_Prompt, Listing_Copy

Each cartridge has:
- Input contract
- Output contract
- Validation rules
- Failure modes

---

## Validation System
Checks:
- Contract completeness
- Usability
- Consistency
- Tool compatibility
- Hallucination

Fail = STOP

---

## Continuity System
Continuity Packet:
- Current stage
- Completed work
- Artifacts
- Next step

Used for resume across chats.

---

## Execution Protocol
Commands:
- PREFLIGHT
- EXECUTE: Stage X
- RESUME
- RETRY
- FIX

Rules:
- One stage per turn
- Always validate
- Always produce artifact
- Always output continuity

---

## Evolution Path
Tier 1: Manual system (current)
Tier 2: Registry + templates
Tier 3: Semi-automation
Tier 4: Dashboard UI
Tier 5: Automation engine
Tier 6: Full OS

---

## Key Principles
- System > prompt
- Context > clever wording
- Routing > forcing LLM
- Validation > trust
- Artifacts > memory

---

## End State
A deterministic, reusable, long-horizon LLM execution system.
