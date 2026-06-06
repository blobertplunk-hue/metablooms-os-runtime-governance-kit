# SANDBOX OPERATING RULES (COMPACT)

## Core Rules

1. Keep processes ≤ 60 for sustained work
2. Never wait on large PID sets (avoid `wait $pids`)
3. Prefer staggered spawning over burst spawning at high counts
4. Keep memory ≤ 512MB for reliable execution
5. Prefer streaming writes over large in-memory objects
6. Keep file descriptors ≤ 256 when combined with other load
7. Limit sustained tasks to ≤ 5 seconds near edge
8. Avoid combining max values across multiple axes simultaneously

---

## Safe Patterns

- spawn → sleep → cleanup (no-wait model)
- staggered process creation
- incremental workload buildup
- isolate heavy operations per stage

---

## Dangerous Patterns

- large PID + wait synchronization
- high memory + high process count
- long duration + high concurrency
- stacking all limits simultaneously

---

## Fail Signals

- missing output
- partial logs
- abrupt termination
- execution reset

---

## Design Principle

Operate inside a conservative envelope unless explicitly testing boundaries.
