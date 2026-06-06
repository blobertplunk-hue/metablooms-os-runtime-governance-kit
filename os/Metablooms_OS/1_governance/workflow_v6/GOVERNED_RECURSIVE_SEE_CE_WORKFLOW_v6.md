# Claude Bundle Governed Recursive SEE+CE Workflow v6
# AMEND-0005 through AMEND-0008 | SEE-backed | 20260426

---

## What changed from v5 and why

Four amendments applied based on CE+SEE research synthesis conducted 20260426:

- **AMEND-0005**: Mid-chunk interrupt trigger (intra-turn circuit breaker)
- **AMEND-0006**: Autonomous sidecar generation (reactive artifact creation)
- **AMEND-0007**: Claude memory bridge (cross-session state persistence)
- **AMEND-0008**: Runtime infrastructure layer (execution-time intervention)

All prior rules from v1-v5 remain in force. These are additive.

---

## AMEND-0005 — Mid-Chunk Interrupt Trigger

**Problem it fixes:** The learning loop previously fired only at end-of-chunk. Failures that emerged mid-chunk (canmore routing, tool runaway, SEE source gaps) could compound through remaining artifacts before being captured.

**Evidence:** "Add intermediate validation steps. Don't just validate final outputs. Validate outputs at key handoff points, especially before irreversible actions." "A corrupted memory at step 5 doesn't just break that step — it poisons every subsequent reflection, plan, and action."

### New rule: Intra-Chunk Interrupt Conditions

After processing each artifact within a chunk (not just at end-of-chunk), evaluate ALL of the following:

```
IC-1: Did this artifact require more than 2 tool retry attempts?
IC-2: Did a canmore/canvas route attempt occur?
IC-3: Did a SEE search return 0 relevant results?
IC-4: Did a claim get made without artifact evidence?
IC-5: Did the artifact reveal a pattern seen in 2+ prior artifacts?
IC-6: Did output fail any T1_DETERMINISTIC gate check?
```

If **any** IC condition fires:
1. **PAUSE** chunk processing immediately after the current artifact.
2. Write `INTRA_CHUNK_INTERRUPT_RECEIPT_v1.json` with: artifact_id, IC condition(s) triggered, evidence, proposed_action.
3. Execute W0-W1 (Observe → Classify) from the self-improvement loop.
4. If classification is `defect` or `gap`: execute W2-W3 (Study → Amend) before resuming.
5. If classification is `friction` or `success_pattern`: log to ISSUE_LESSON_LOG and resume.
6. **NEVER silently continue past an IC trigger.**

### Interrupt receipt template

```json
{
  "receipt_type": "INTRA_CHUNK_INTERRUPT",
  "artifact_id": "<id>",
  "chunk_position": "<n of total>",
  "ic_conditions_fired": [],
  "evidence": "",
  "classification": "defect | gap | friction | success_pattern",
  "proposed_action": "pause_and_amend | log_and_continue | escalate",
  "resumed": false
}
```

---

## AMEND-0006 — Autonomous Sidecar Generation

**Problem it fixes:** The tool failure mode bundle (and prior similar artifacts) was created manually because Robert noticed the problem and requested it. The workflow had no mechanism to detect a recurring failure class and automatically package a remediation sidecar.

**Evidence:** "After DevOps Agent resolves three DynamoDB throttling incidents over a month, the Learning Agent identifies the recurring pattern and generates a learned skill that accelerates future investigations of the same class." "Artifacts can serve as a versioned data and model registry... making artifacts the 'contracts' that define inter-workflow dependencies and automations."

### New rule: Autonomous Sidecar Trigger Thresholds

The workflow must autonomously generate a named sidecar bundle when any of the following thresholds are crossed **within a single session or across receipts in the current bundle**:

| Trigger Class | Threshold | Sidecar Generated |
|---|---|---|
| Same IC condition fires on 2+ artifacts | ≥2 instances | `FAILURE_CLASS_<IC>_SIDECAR_v1.zip` |
| Same tool routing failure class | ≥2 instances | `TOOL_FAILURE_<CLASS>_SIDECAR_v1.zip` |
| Same SEE source gap | ≥2 searches return 0 results | `SEE_GAP_<TOPIC>_SIDECAR_v1.zip` |
| Amendment proposed but not yet validated | After W3 completes | `AMENDMENT_CANDIDATE_<ID>_SIDECAR_v1.zip` |
| New success pattern identified | Immediately after SP promotion | `SUCCESS_PATTERN_<ID>_SIDECAR_v1.zip` |

### Sidecar contents (minimum)

Every auto-generated sidecar must contain:
- `README_<SIDECAR_NAME>.md` — what it is, why it was generated, trigger evidence
- `TRIGGER_EVIDENCE_v1.json` — receipt IDs, artifact IDs, IC conditions, SHA values
- Relevant governance artifacts (router rules, block receipts, amendment candidates)
- `SIDECAR_INDEX_v1.json` with SHA256 for every file

### Sidecar naming and placement

Sidecars are written to `/mnt/data/workflow_sidecars/` and added to ARTIFACT_MANIFEST before the end-of-chunk receipt. They are **not** optional. If the sidecar cannot be written (disk, tool failure), write a `SIDECAR_BLOCKED_RECEIPT_v1.json` instead.

---

## AMEND-0007 — Claude Memory Bridge

**Problem it fixes:** Every ChatGPT session cold-starts. The amendment ledger, active success patterns, regression checklist version, and current stage pointer all have to be re-read from the bundle ZIP each time. The learning system has earned cross-session memory but doesn't use it.

**Evidence:** "Capabilities like memory are also increasing the value of signals loops. These technologies enable AI systems to retain context and learn from user feedback — driving greater personalization and improving customer retention." "One of the most powerful mechanisms in these agent loops is the use of persistent context files that carry knowledge forward between iterations."

### New rule: End-of-Session Memory Sync

At the end of every session (before final export), write `CLAUDE_MEMORY_SYNC_v1.json` containing the fields below. This file is handed to Claude (this environment) to load into the memory system, creating cross-session state that survives ChatGPT's cold start.

```json
{
  "sync_utc": "<ISO timestamp>",
  "bundle_version": "<v33+>",
  "current_stage": "<GW5U...>",
  "baseline_sha": "<SIR25 or candidate SHA>",
  "active_amendments": ["AMEND-0001", "AMEND-0002", ...],
  "active_success_patterns": ["SP-0001", "SP-0002", ...],
  "regression_checklist_version": "v4",
  "open_ic_triggers": [],
  "pending_sidecars": [],
  "known_blockers": [],
  "next_chunk": [],
  "deferred_items": [],
  "session_note": "<one sentence summary>"
}
```

### Claude's role in the bridge

When Robert uploads a new bundle or mentions starting a new session, Claude reads `CLAUDE_MEMORY_SYNC_v1.json` and stores the `current_stage`, `baseline_sha`, `active_amendments`, and `session_note` into the memory system. On the next session, Claude provides the memory-loaded state as a verified pre-boot summary — eliminating the re-read-the-whole-bundle startup cost.

---

## AMEND-0008 — Runtime Infrastructure Layer

**Problem it fixes:** The workflow's governance runs at preflight and end-of-chunk. There is no execution-time intervention — the equivalent of VIGIL's mid-run diagnostics or the circuit breaker patterns described in production AI systems.

**Evidence:** "We introduce AI Runtime Infrastructure, a distinct execution-time layer that operates above the model and below the application, actively observing, reasoning over, and intervening in agent behavior to optimize task success, latency, token efficiency, reliability, and safety while the agent is running." "Agent middleware is emerging as the standard abstraction layer for production systems... intercepting the loop at before_model, after_model, and modify_model_request."

### New rule: Per-Artifact Runtime Pulse

Before **and** after each artifact is processed, run a lightweight runtime pulse check:

**Pre-artifact pulse (before processing begins):**
```
RP-PRE-1: Is this artifact in the current queue? (T1: block if not)
RP-PRE-2: Is the artifact SHA known/verified? (T1: block if hash unknown)
RP-PRE-3: Does this artifact class require SEE? (T2: flag if SEE not pre-loaded)
RP-PRE-4: Is there an open IC trigger from the prior artifact? (T1: block until resolved)
```

**Post-artifact pulse (after processing completes):**
```
RP-POST-1: Does the receipt exist and contain required fields? (T1: block export if missing)
RP-POST-2: Are output artifact SHAs declared in the receipt? (T1: block if missing)
RP-POST-3: Did the artifact trigger any IC condition? (T2: interrupt if yes)
RP-POST-4: Did a new success pattern emerge? (T2: log and optionally generate sidecar)
```

Pulse checks are cheap (they read state already in context). They do not call external tools. They write to the `RUNTIME_PULSE_LOG_v1.jsonl` append-only ledger.

### Runtime pulse log format

```jsonl
{"artifact_id":"<id>","phase":"pre|post","pulse_id":"RP-PRE-1","tier":"T1","decision":"pass|block|flag","evidence":"","ts":"<ISO>"}
```

---

## Updated regression checklist additions (v5)

Add to WORKFLOW_REGRESSION_CHECKLIST_v5.md:

- [ ] Intra-chunk IC trigger evaluated after each artifact (not just end-of-chunk)
- [ ] If IC trigger fired: INTRA_CHUNK_INTERRUPT_RECEIPT written before continuing
- [ ] Autonomous sidecar generated if threshold crossed (2+ same-class failures)
- [ ] Sidecar written to `/mnt/data/workflow_sidecars/` with index and SHAs
- [ ] CLAUDE_MEMORY_SYNC_v1.json written at end of every session
- [ ] Runtime pulse log entries present for each artifact (pre and post)
- [ ] No artifact processed if RP-PRE-4 (open IC trigger) is unresolved

---

## Updated success pattern additions

Add to SUCCESS_PATTERN_REGISTRY_v4.json:

```json
{
  "pattern_id": "AMEND-0006-AUTO-SIDECAR",
  "name": "Autonomous sidecar generation on threshold crossing",
  "source": "SEE research: AWS DevOps Agent learned skills pattern",
  "why_it_works": "Recurring failure classes become self-documenting remediation artifacts without human intervention. Robert's role shifts from noticing the pattern to reviewing the auto-generated sidecar.",
  "reuse_rule": "Any class of failure that recurs 2+ times gets a sidecar. No exceptions."
}
```

---

## Workflow version summary

| Version | Key addition |
|---|---|
| v1 | Chunked processing + receipts |
| v2 | Self-improvement loop (W0-W5) |
| v3 | HTML governance gates |
| v4 | Scoped governance taxonomy |
| v5 | Nomotic runtime governance, PDP/PEP |
| **v6** | **Mid-chunk interrupt, autonomous sidecars, memory bridge, runtime pulse** |

