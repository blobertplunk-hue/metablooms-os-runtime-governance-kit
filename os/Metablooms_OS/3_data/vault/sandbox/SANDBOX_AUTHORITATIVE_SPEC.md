# SANDBOX AUTHORITATIVE SPEC (CONSOLIDATED)

## Overview
Empirical model of the ChatGPT UI sandbox derived from staged probes across:
- Process (PID) limits
- Time interaction
- Memory pressure
- File descriptor limits
- Disk I/O
- Composite load behavior

---

## 1. Process Limits
- Stable: ≤ 75 processes (short duration, no-wait model)
- Degradation band: ~75–79
- Failure: ≥ 80 (even low duration, no-wait)

### Additional constraints
- Collective wait on many PIDs introduces instability earlier
- Burst spawning is tolerated more than synchronized waits

---

## 2. Time Interaction
- Short-lived tasks are safe within process limits
- Sustained tasks introduce additional watchdog pressure
- Synchronization (wait on many processes) is a primary failure trigger

---

## 3. Memory Limits
- Stable allocations: up to ~768MB confirmed
- 1024MB possible but interacts with other load factors
- Heap allocation is more sensitive than streaming disk writes

---

## 4. File Descriptor Limits
- Verified open handles: 128, 256, 512, 1024
- No immediate failure at 1024 in isolation
- Likely contributes to composite load failure

---

## 5. Disk Behavior
- Writes ≥ 250MB confirmed stable
- Larger writes show partial or interrupted behavior under load
- Disk is less sensitive than RAM under equivalent sizes

---

## 6. Composite Load Model

### Stable composite region
- 256–512MB memory
- ≤ 40–60 processes
- ≤ 256–512 FDs
- ≤ 2–5 seconds duration

### Near-edge region
- 512–768MB
- ~60 processes
- ~512 FDs
- 2–10 seconds

### Failure characteristics
- abrupt termination
- no graceful error
- partial output artifacts
- runtime reset behavior

---

## 7. Failure Modes
- Kernel/watchdog termination
- Selector overload (waiting on many PIDs)
- Cumulative resource pressure
- Non-linear interaction across dimensions

---

## 8. System Model

The sandbox behaves as:

f(process_count, memory, file_descriptors, time, synchronization)

NOT as independent scalar limits.

---

## 9. Key Insight

Limits are:
- interaction-based
- time-weighted
- synchronization-sensitive

---

## 10. Practical Envelope

For reliable execution:

- Processes: ≤ 60
- Memory: ≤ 512MB
- FDs: ≤ 256–512
- Duration: ≤ 5s
- Avoid collective wait on large PID sets
