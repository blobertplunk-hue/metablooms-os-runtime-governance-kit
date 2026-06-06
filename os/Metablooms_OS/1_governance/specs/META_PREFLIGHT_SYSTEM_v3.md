# META PREFLIGHT SYSTEM (MPS v3.0)

## PURPOSE
Universal, enforced, adaptive, state-aware preflight system that prevents predictable failures BEFORE execution.

---

# 🔒 CORE INVARIANT
NO TASK MAY EXECUTE WITHOUT PASSING PREFLIGHT

If ANY required field is:
- unknown
- unbounded
- unverified

→ FAIL CLOSED (STOP)

---

# 🧠 FULL EXECUTION PIPELINE

STATE CAPTURE
↓
SEE (Task-Specific Research)
↓
TASK PREFLIGHT
↓
UNIVERSAL PREFLIGHT
↓
RISK GATE
↓
EXECUTION GATE
↓
EXECUTE
↓
VERIFY
↓
SYSTEM UPDATE

---

# 🧱 STATE CAPTURE (REQUIRED)

## Artifact: state_snapshot.json

Must include:
- total_space
- used_space
- free_space
- top directories by size
- largest files
- critical paths (Photos, Downloads, etc.)

RULE:
IF missing → STOP

---

# 🧱 TASK-SPECIFIC PREFLIGHT (SEE REQUIRED)

Must perform web.run research.

Extract:
- failure modes
- environment risks
- best practices
- constraints

FAIL if:
- no research performed

---

# 🧱 UNIVERSAL PREFLIGHT (FULL)

## 1. INTENT CLARITY
Define:
- objective
- scope
- output

FAIL if unclear.

---

## 2. SYSTEM CONTEXT
Verify:
- environment
- filesystem
- runtime
- constraints

FAIL if ambiguous.

---

## 3. INPUT DISCOVERY
Must know:
- targets
- count
- types
- sizes

FAIL if unknown.

---

## 4. DEPENDENCIES
Verify:
- tools
- permissions
- required files

FAIL if missing.

---

## 5. IMPACT FORECAST
Compute:
- input size
- output size
- duplication factor

RULE:
output ≤ 70% available space

FAIL if unsafe.

---

## 6. RESOURCE VALIDATION
Verify:
- disk
- memory
- capacity

FAIL if insufficient.

---

## 7. CONSTRAINTS
Define:
- max files
- max output
- max runtime

FAIL if unbounded.

---

## 8. PATH VALIDATION
Verify:
- explicit paths
- correct storage
- no restricted dirs

FAIL if unclear.

---

## 9. TRANSFORMATION MODEL
Define:
- steps
- execution mode
- order

FAIL if undefined.

---

## 10. DUPLICATION CHECK
RULE:
No >1.5x data growth

FAIL if violated.

---

## 11. ROLLBACK
Must define:
- reversal steps
- safe restore

FAIL if not possible.

---

## 12. LOGGING
Must define:
- log outputs
- traceability

FAIL if missing.

---

## 13. DRY RUN
Simulate:
- file changes
- size impact

FAIL if skipped.

---

## 14. RISK CLASSIFICATION
LOW / MEDIUM / HIGH

FAIL if missing.

---

## 15. HUMAN CHECKPOINT
Required if:
- large operations
- deletion
- uncertainty

---

# 🧱 RISK GATE (NEW)

## Artifact: risk_gate.json

Must include:
- risk_level
- backup_verified
- rollback_possible
- decision

RULE:
IF HARD_STOP → STOP SYSTEM

---

# 🧱 EXECUTION GATE

ALL must pass:

✔ intent  
✔ context  
✔ inputs  
✔ dependencies  
✔ forecast  
✔ resources  
✔ constraints  
✔ paths  
✔ process  
✔ duplication safe  
✔ rollback  
✔ logging  
✔ dry run  
✔ risk classified  
✔ SEE complete  

FAIL ANY → STOP

---

# 🧾 REQUIRED ARTIFACTS

- state_snapshot.json
- preflight_report.json
- risk_gate.json

---

# 🔁 SYSTEM RULE

Every failure → new permanent check

---

# 🔒 FINAL RULE

Execution prohibited until ALL layers pass.
