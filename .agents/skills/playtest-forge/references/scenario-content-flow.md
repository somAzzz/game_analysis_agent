# Content, choices, routes, and endings

Export or reconstruct the event/action/choice/ending graph. Distinguish:

- declared content;
- reachable content under valid state;
- triggered content;
- presented choices;
- selected choices;
- effects actually applied;
- final outcome classification.

Check missing IDs, dead ends, cycles, contradictory prerequisites, ordering
dependencies, unreachable branches, duplicate choices, misleading copy,
effect/description mismatches, and endings inconsistent with final state.

Use persona workers to assess whether choices communicate tradeoffs and permit
distinct intent. Use deterministic traversal and boundary probes to prove
reachability and effect application. If a route is absent, repair graph or
trigger logic before tuning its reward. Preserve intentionally rare content;
low frequency alone is not a defect without the design contract.
