# Migration to another game or engine

Keep the Skill workflow unchanged and replace the adapter layer.

## Required adapter capabilities

Map these concepts even when names differ:

- launch/reset with explicit source revision, scenario, difficulty, and seed;
- observe typed public state and legal actions/choices;
- apply one action/choice and return the transition;
- export outcomes, content catalogs/graphs, and validator results;
- isolate reports per cell and support terminal partial/failure status;
- run focused engine tests and deterministic cohorts;
- identify editable mechanic/parameter sources and create a diff.

Godot scripts, Unity tests, Unreal commandlets, a web simulator, or a custom
server may implement the adapter. Do not place engine-specific commands in the
core workflow.

## Create the project profile

Add one reference containing:

- runtime/install command and pinned version;
- repository/source pin and writable worktree strategy;
- scenario/persona/action/state mappings;
- design invariants and designed failures;
- report schemas and catalog paths;
- focused/full test commands;
- allowed mechanism classes and forbidden edit areas;
- privacy/public-bundle rules.

Provide project scripts for preflight, campaign, and repair verification only
when they exist. Otherwise document the equivalent typed service calls. The
Skill must fail with remediation when a capability is missing, not silently
use this repository's scripts.

## Migration acceptance

Before advertising support, prove one deterministic baseline, one persona
playthrough or declared automation-only limitation, one intentionally rejected
candidate, fixed/holdout separation, invariant preservation, and a complete
evidence bundle on the new project.
