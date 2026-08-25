# Boundary, robustness, exploits, and invariants

Enumerate state bounds, forbidden combinations, pipeline progress guarantees,
and semantic invariants. Probe zero, maximum, just-inside, just-outside,
repeated application, missing content, invalid IDs, cancellation, timeout, and
save/resume boundaries.

Prioritize:

1. crash, corruption, stalled pipeline, invalid ending, or impossible state;
2. rules contradiction or exploit;
3. balance regression;
4. presentation anomaly.

Record the minimal transition that violates the invariant. Repair the state
transition or validation boundary before adjusting economy/difficulty values.
After the focused fix, rerun the complete invariant suite plus representative
normal play; a boundary fix that blocks valid player recovery is a regression.

Never weaken a validator expected value to make a candidate pass. If the
design rule itself changes, revise and independently approve the design
contract in a separate change before the repair experiment.
