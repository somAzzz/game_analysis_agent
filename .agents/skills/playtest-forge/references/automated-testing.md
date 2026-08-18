# Automated testing

## Build the matrix

Cross product only variables that answer the objective:

- player policy or persona surrogate;
- scenario/difficulty;
- fixed seeds and separately frozen holdout seeds;
- bounded duration or termination condition;
- baseline/candidate revision;
- one parameter value for a sensitivity sweep, when needed.

Keep each cell isolated and resumable. Record expected, completed, partial,
failed, and cancelled cells. Do not aggregate until every required cell has a
terminal truth state.

For a difficulty-specific review, choose exactly one committed lane:
`config/matrix.easy.yaml`, `config/matrix.normal.yaml`,
`config/matrix.hard.yaml`, or `config/matrix.realistic.yaml`. The default is
Normal. Each lane must bind the same difficulty in simulation, boundary, and
persona cells; do not reuse one lane's evidence as another difficulty's proof.

## Record per step

Capture run/cell ID, seed, step/week, available actions, selected action,
triggered content, before/after state, termination, runtime revision, and
contract version. Validate ranges, required IDs, action legality, pipeline
progress, and state transition consistency while running.

## Aggregate

Compute distributions rather than only averages:

- outcome/ending rate and time-to-failure;
- resource floor, peak pressure, recovery time, and saturation;
- action/event/choice coverage and pick rate;
- persona separation and cross-persona convergence;
- invariant counts and invalid pipeline states;
- validity, fallback, provider-error, retry, and partial rates.

Cluster failures by mechanism-relevant state, not merely ending label. Cite the
first entry into a cluster and representative paths before and after it.

## Sensitivity before editing

For an uncertain parameter, sweep a narrow range around baseline without
changing code structure. Prefer monotonic metrics and record discontinuities.
If multiple parameters interact, test one axis first or use a declared
factorial design; do not tune several values from one aggregate.
