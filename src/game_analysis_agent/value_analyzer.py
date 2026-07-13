"""Value / balance reasonableness analyzer.

Inputs: ``action_pick_rates.csv`` + ``event_trigger_rates.csv`` +
``choice_pick_rates.csv`` (computed by :mod:`game_analysis_agent.analytics`).
Optional inputs: ``raw_runs.jsonl`` + ``action_catalog.json`` for the
new action-group / crisis-response / ending-contradiction / route-separation
analyses introduced in v0.2 (T06).

The analyzer is statistical, not LLM-driven — its output is meant to be
consumed by the ``value_reviewer`` agent which adds narrative explanation
on top. Findings are emitted as :class:`game_analysis_agent.schemas.ValueFinding`
rows written to ``value_report.json`` and ``route_report.json``.

Heuristics:

* **Dominant action**: pick_rate_per_run > 0.80  → "必选".
* **Dead action**: pick_rate_per_run < 0.05  → "无人选".
* **Dominant choice** (per event): rate_per_event > 0.85 → "该选项被碾压".
* **Far-from-balanced outcome**: ending distribution within a single
  policy is > 90% on one ending → "玩法单一".

Plus, when ``raw_runs.jsonl`` is present:

* **Action group dominance**: aggregate pick counts by action tag (e.g.
  ``recovery``, ``study``, ``work``) per policy; flag over-picked groups.
* **Crisis response**: when a week starts in a crisis state (low money,
  high stress, high hunger, high visa risk), the chosen actions should
  belong to the matching coping group; otherwise the difficulty knobs
  are wrong.
* **Ending contradiction**: pair ``final_ending_id`` with the final-week
  state and flag "happy ending with broken body" combinations.
* **Route separation score**: compute each policy's mean of 5 axis
  stats and measure how far it is from the balanced baseline; tiny
  distances → "路线没有分化".
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from game_analysis_agent.schemas import ValueFinding

DOMINANT_PICK_RATE = 0.80
DEAD_PICK_RATE = 0.05
DOMINANT_CHOICE_RATE = 0.85
ENDINGLE_DOMINANCE = 0.90

# T06 thresholds.
DEFAULT_RECOVERY_GROUP_RATE = 2.5
DEFAULT_ESCAPE_GROUP_RATE = 2.0
DEFAULT_STUDY_GROUP_RATE_MIN = 1.0
DEFAULT_WORK_GROUP_RATE_MIN = 0.5
DEFAULT_CRISIS_RESPONSE_THRESHOLD = 0.4
DEFAULT_CRISIS_RESPONSE_ERROR = 0.2
DEFAULT_HUNGER_CRISIS_THRESHOLD = 80.0
DEFAULT_STRESS_CRISIS_THRESHOLD = 80.0
DEFAULT_LOW_MONEY_THRESHOLD = 200.0
DEFAULT_VISA_RISK_THRESHOLD = 70.0
DEFAULT_CONTRADICTION_SCORE_HIGH = 100.0
DEFAULT_CONTRADICTION_SCORE_LOW = 30.0
DEFAULT_ROUTE_DISTANCE_WARNING = 0.15
DEFAULT_ROUTE_AXES = ("academic", "work", "social", "admin", "slacker")

# Action tag → action-id keyword heuristic. Used when ``action_catalog.json``
# is not present. Keeping this in one place makes it easy to override per game.
ACTION_GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "recovery": ("sleep", "rest", "nap", "recover", "meditat", "yoga", "therapy"),
    "study": ("study", "library", "lecture", "homework", "exam", "course"),
    "admin": ("visa", "registration", "office", "insurance", "permit", "anmel"),
    "work": ("work", "shift", "mini_job", "tutoring", "part_time", "freelance"),
    "social": ("chat", "party", "friend", "wechat", "karaoke", "discord", "social", "date"),
    "food": ("cook", "eat", "meal", "grocer", "restaurant", "dinner", "lunch"),
    "escape": ("bilibili", "scroll", "binge", "video", "netflix", "tiktok"),
}


def _infer_action_group(action_id: str) -> str:
    """Fallback group classification from action-id keywords."""
    lowered = action_id.lower()
    for group, keywords in ACTION_GROUP_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                return group
    return "other"


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyze_values(
    *,
    action_csv: Path | None = None,
    event_csv: Path | None = None,
    choice_csv: Path | None = None,
    ending_csv: Path | None = None,
    dominant_pick: float = DOMINANT_PICK_RATE,
    dead_pick: float = DEAD_PICK_RATE,
    dominant_choice: float = DOMINANT_CHOICE_RATE,
    ending_dominance: float = ENDINGLE_DOMINANCE,
) -> list[ValueFinding]:
    """Return a list of :class:`ValueFinding` rows."""

    findings: list[ValueFinding] = []
    counter = _FindingCounter()

    if action_csv is not None:
        for row in load_csv(action_csv):
            policy = row.get("policy", "")
            action_id = row.get("action_id", "")
            try:
                metric_name = (
                    "pick_share" if row.get("pick_share") not in (None, "") else "rate_per_run"
                )
                rate = float(row.get(metric_name, 0.0))
                count = int(row.get("count", 0))
            except (TypeError, ValueError):
                continue
            if rate >= dominant_pick and count >= 5:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("action_dominant"),
                        scope="action",
                        target_id=f"{policy}:{action_id}",
                        severity="warning",
                        metric=metric_name,
                        value=rate,
                        threshold=dominant_pick,
                        description=(
                            f"Action `{action_id}` (policy={policy}) is picked "
                            f"{rate:.1%} of action picks — probable 'must-pick'."
                        ),
                    )
                )
            elif rate <= dead_pick and count >= 0:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("action_dead"),
                        scope="action",
                        target_id=f"{policy}:{action_id}",
                        severity="info",
                        metric=metric_name,
                        value=rate,
                        threshold=dead_pick,
                        description=(
                            f"Action `{action_id}` (policy={policy}) was picked "
                            f"{rate:.1%} of action picks — likely 'no value'."
                        ),
                    )
                )

    if choice_csv is not None:
        by_event: dict[tuple[str, str], list[tuple[str, int, float]]] = defaultdict(list)
        for row in load_csv(choice_csv):
            policy = row.get("policy", "")
            event_id = row.get("event_id", "")
            choice_id = row.get("choice_id", "")
            try:
                rate = float(row.get("rate_per_event", 0.0))
                count = int(row.get("count", 0))
            except (TypeError, ValueError):
                continue
            if not event_id or not choice_id:
                continue
            by_event[(policy, event_id)].append((choice_id, count, rate))
        for (policy, event_id), entries in by_event.items():
            if not entries:
                continue
            entries.sort(key=lambda item: item[2], reverse=True)
            top_choice, top_count, top_rate = entries[0]
            if top_rate >= dominant_choice and top_count >= 3:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("choice_dominant"),
                        scope="choice",
                        target_id=f"{policy}:{event_id}:{top_choice}",
                        severity="warning",
                        metric="rate_per_event",
                        value=top_rate,
                        threshold=dominant_choice,
                        description=(
                            f"Choice `{top_choice}` dominates event `{event_id}` "
                            f"({top_rate:.1%} of triggers)."
                        ),
                    )
                )

    if event_csv is not None:
        for row in load_csv(event_csv):
            policy = row.get("policy", "")
            event_id = row.get("event_id", "")
            try:
                rate = float(row.get("rate_per_run", 0.0))
            except (TypeError, ValueError):
                continue
            if rate <= 0.005:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("event_rare"),
                        scope="event",
                        target_id=f"{policy}:{event_id}",
                        severity="info",
                        metric="rate_per_run",
                        value=rate,
                        threshold=0.005,
                        description=(
                            f"Event `{event_id}` only triggered in "
                            f"{rate:.2%} of runs — likely unreachable."
                        ),
                    )
                )

    if ending_csv is not None:
        by_policy: dict[str, list[tuple[str, int, float]]] = defaultdict(list)
        for row in load_csv(ending_csv):
            policy = row.get("policy", "")
            ending_id = row.get("ending_id", "")
            try:
                rate = float(row.get("rate", 0.0))
                count = int(row.get("count", 0))
            except (TypeError, ValueError):
                continue
            by_policy[policy].append((ending_id, count, rate))
        for policy, endings in by_policy.items():
            endings.sort(key=lambda item: item[2], reverse=True)
            if not endings:
                continue
            top = endings[0]
            if top[2] >= ending_dominance and top[1] >= 5:
                findings.append(
                    ValueFinding(
                        finding_id=counter.next("ending_dominant"),
                        scope="ending",
                        target_id=f"{policy}:{top[0]}",
                        severity="warning",
                        metric="rate",
                        value=top[2],
                        threshold=ending_dominance,
                        description=(
                            f"Policy `{policy}` reaches `{top[0]}` in "
                            f"{top[2]:.1%} of runs — play style feels single-track."
                        ),
                    )
                )

    return findings


class _FindingCounter:
    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)

    def next(self, prefix: str) -> str:
        self._counters[prefix] += 1
        return f"{prefix}-{self._counters[prefix]:04d}"


def write_value_report(
    findings: Iterable[ValueFinding],
    path: Path,
    *,
    meta: dict[str, Any] | None = None,
) -> int:
    findings_list = list(findings)
    payload: dict[str, Any] = {
        "finding_count": len(findings_list),
        "by_kind": _group_findings(findings_list),
        "findings": [finding.model_dump(mode="json") for finding in findings_list],
    }
    if meta is not None:
        payload["meta"] = meta
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(findings_list)


def _group_findings(findings: list[ValueFinding]) -> dict[str, int]:
    grouped: dict[str, int] = defaultdict(int)
    for finding in findings:
        key = finding.finding_id.rsplit("-", 1)[0]
        grouped[key] += 1
    return dict(sorted(grouped.items()))


def analyze_and_write(report_dir: Path) -> list[ValueFinding]:
    findings = analyze_values(
        action_csv=report_dir / "action_pick_rates.csv",
        event_csv=report_dir / "event_trigger_rates.csv",
        choice_csv=report_dir / "choice_pick_rates.csv",
        ending_csv=report_dir / "ending_distribution.csv",
    )
    write_value_report(findings, report_dir / "value_report.json")
    route = analyze_route_metrics(
        raw_runs_path=report_dir / "raw_runs.jsonl",
        action_catalog_path=report_dir / "action_catalog.json",
    )
    write_route_report(route, report_dir / "route_report.json")
    return findings


# ---------------------------------------------------------------------------
# Route / group / crisis analyses (T06)
# ---------------------------------------------------------------------------


def load_action_tags(
    raw_runs_path: Path | None,
    action_catalog_path: Path | None,
) -> dict[str, str]:
    """Build an ``action_id -> group`` mapping.

    Preference order:

    1. ``action_catalog.json`` next to the report — populated by
       :func:`tools.run_gameplay_agent.cmd_export` from the game project.
    2. Keyword heuristic via :data:`ACTION_GROUP_KEYWORDS`.
    """
    if action_catalog_path is not None and action_catalog_path.exists():
        try:
            payload = json.loads(action_catalog_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        actions = payload.get("actions") if isinstance(payload, dict) else None
        if isinstance(actions, list):
            mapping: dict[str, str] = {}
            for entry in actions:
                if not isinstance(entry, dict):
                    continue
                action_id = str(entry.get("id") or "").strip()
                if not action_id:
                    continue
                tags = entry.get("tags") or []
                if not isinstance(tags, list) or not tags:
                    mapping[action_id] = _infer_action_group(action_id)
                    continue
                first = str(tags[0]).lower()
                mapping[action_id] = first if first in ACTION_GROUP_KEYWORDS else first
            if mapping:
                return mapping

    # Heuristic fallback: scan raw_runs to collect every action id we see
    # and tag each via :func:`_infer_action_group`.
    if raw_runs_path is not None and raw_runs_path.exists():
        try:
            runs = [
                json.loads(line)
                for line in raw_runs_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except json.JSONDecodeError:
            runs = []
        seen: dict[str, str] = {}
        for run in runs:
            for week in run.get("weekly_log", []) or []:
                if not isinstance(week, dict):
                    continue
                for action_id in (
                    week.get("selected_action_ids") or week.get("actions") or []
                ):
                    action_id = str(action_id)
                    if action_id not in seen:
                        seen[action_id] = _infer_action_group(action_id)
        return seen
    return {}


def _iter_action_picks(run: dict[str, Any]) -> Iterable[str]:
    """Yield every action id chosen across the run."""
    for week in run.get("weekly_log", []) or []:
        if not isinstance(week, dict):
            continue
        for key in ("selected_action_ids", "actions"):
            for action_id in week.get(key, []) or []:
                yield str(action_id)


def _after_state(week: dict[str, Any]) -> dict[str, Any]:
    state = week.get("after_state")
    if isinstance(state, dict):
        return state
    state = week.get("state")
    if isinstance(state, dict):
        return state
    return {}


def analyze_action_groups(
    runs: list[dict[str, Any]],
    action_tags: dict[str, str],
    *,
    recovery_threshold: float = DEFAULT_RECOVERY_GROUP_RATE,
    escape_threshold: float = DEFAULT_ESCAPE_GROUP_RATE,
    study_threshold_min: float = DEFAULT_STUDY_GROUP_RATE_MIN,
    work_threshold_min: float = DEFAULT_WORK_GROUP_RATE_MIN,
) -> list[ValueFinding]:
    """Flag over-picked (recovery / escape) and under-picked (study / work) groups."""
    findings: list[ValueFinding] = []
    by_policy: dict[str, Counter[str]] = defaultdict(Counter)
    totals: Counter[str] = Counter()
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        totals[policy] += 1
        for action_id in _iter_action_picks(run):
            group = action_tags.get(action_id, "other")
            by_policy[policy][group] += 1

    # Always check the 5 nominal groups per policy, even when no action
    # in that group was ever picked. This lets us flag a policy that
    # *never* touches work or study.
    groups_to_check = ("recovery", "escape", "study", "work")
    for policy, group_counts in sorted(by_policy.items()):
        run_count = max(1, totals[policy])
        for group in groups_to_check:
            count = group_counts.get(group, 0)
            rate = count / run_count
            if (
                group == "recovery"
                and rate > recovery_threshold
                and count > 0
            ):
                findings.append(
                    ValueFinding(
                        finding_id=f"group_dominant-{len(findings) + 1:04d}",
                        scope="action_group",
                        target_id=f"{policy}:recovery",
                        severity="warning",
                        metric="picks_per_run",
                        value=round(rate, 3),
                        threshold=recovery_threshold,
                        description=(
                            f"Recovery group over-picked under policy `{policy}` "
                            f"({rate:.2f}/run, threshold={recovery_threshold})."
                        ),
                    )
                )
            elif (
                group == "escape"
                and rate > escape_threshold
                and count > 0
            ):
                findings.append(
                    ValueFinding(
                        finding_id=f"group_dominant-{len(findings) + 1:04d}",
                        scope="action_group",
                        target_id=f"{policy}:escape",
                        severity="warning",
                        metric="picks_per_run",
                        value=round(rate, 3),
                        threshold=escape_threshold,
                        description=(
                            f"Escape group over-picked under policy `{policy}` "
                            f"({rate:.2f}/run, threshold={escape_threshold})."
                        ),
                    )
                )
            elif group == "study" and totals[policy] >= 5 and rate < study_threshold_min:
                findings.append(
                    ValueFinding(
                        finding_id=f"group_underused-{len(findings) + 1:04d}",
                        scope="action_group",
                        target_id=f"{policy}:study",
                        severity="info",
                        metric="picks_per_run",
                        value=round(rate, 3),
                        threshold=study_threshold_min,
                        description=(
                            f"Study group under-picked under policy `{policy}` "
                            f"({rate:.2f}/run, threshold={study_threshold_min})."
                        ),
                    )
                )
            elif group == "work" and totals[policy] >= 5 and rate < work_threshold_min:
                findings.append(
                    ValueFinding(
                        finding_id=f"group_underused-{len(findings) + 1:04d}",
                        scope="action_group",
                        target_id=f"{policy}:work",
                        severity="info",
                        metric="picks_per_run",
                        value=round(rate, 3),
                        threshold=work_threshold_min,
                        description=(
                            f"Work group under-picked under policy `{policy}` "
                            f"({rate:.2f}/run, threshold={work_threshold_min})."
                        ),
                    )
                )
    return findings


def analyze_crisis_response(
    runs: list[dict[str, Any]],
    action_tags: dict[str, str],
    *,
    low_money_threshold: float = DEFAULT_LOW_MONEY_THRESHOLD,
    stress_threshold: float = DEFAULT_STRESS_CRISIS_THRESHOLD,
    hunger_threshold: float = DEFAULT_HUNGER_CRISIS_THRESHOLD,
    visa_risk_threshold: float = DEFAULT_VISA_RISK_THRESHOLD,
    response_threshold: float = DEFAULT_CRISIS_RESPONSE_THRESHOLD,
    response_error: float = DEFAULT_CRISIS_RESPONSE_ERROR,
) -> list[ValueFinding]:
    """When a run enters a crisis state, did the policy respond with the right group?"""
    findings: list[ValueFinding] = []
    # Map: crisis -> expected groups
    crisis_to_group: dict[str, tuple[str, ...]] = {
        "low_money": ("work", "food"),
        "high_stress": ("recovery",),
        "high_hunger": ("food",),
        "high_visa_risk": ("admin",),
    }
    by_policy: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: {crisis: {"hits": 0, "total": 0} for crisis in crisis_to_group}
    )
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        for week in run.get("weekly_log", []) or []:
            if not isinstance(week, dict):
                continue
            state = _after_state(week)
            money = state.get("money")
            stress = state.get("stress")
            hunger = state.get("hunger")
            visa = state.get("visa_progress")
            crisis: str | None = None
            if isinstance(money, (int, float)) and money < low_money_threshold:
                crisis = "low_money"
            elif isinstance(stress, (int, float)) and stress > stress_threshold:
                crisis = "high_stress"
            elif isinstance(hunger, (int, float)) and hunger > hunger_threshold:
                crisis = "high_hunger"
            elif isinstance(visa, (int, float)) and (100 - visa) > visa_risk_threshold:
                crisis = "high_visa_risk"
            if crisis is None:
                continue
            by_policy[policy][crisis]["total"] += 1
            chosen = [
                action_tags.get(str(a), "other")
                for a in (
                    week.get("selected_action_ids") or week.get("actions") or []
                )
            ]
            expected = crisis_to_group[crisis]
            if any(group in expected for group in chosen):
                by_policy[policy][crisis]["hits"] += 1

    for policy, crisis_stats in sorted(by_policy.items()):
        for crisis, counts in sorted(crisis_stats.items()):
            total = counts["total"]
            if total < 3:  # don't fire on tiny samples
                continue
            rate = counts["hits"] / total
            if rate >= response_threshold:
                continue
            severity = "error" if rate < response_error else "warning"
            findings.append(
                ValueFinding(
                    finding_id=f"crisis_response-{len(findings) + 1:04d}",
                    scope="crisis_response",
                    target_id=f"{policy}:{crisis}",
                    severity=severity,
                    metric="response_rate",
                    value=round(rate, 3),
                    threshold=response_threshold,
                    description=(
                        f"Policy `{policy}` responded correctly to `{crisis}` "
                        f"only {rate:.0%} of {total} weeks."
                    ),
                )
            )
    return findings


def analyze_ending_contradictions(
    runs: list[dict[str, Any]],
    *,
    success_score_high: float = DEFAULT_CONTRADICTION_SCORE_HIGH,
    success_score_low: float = DEFAULT_CONTRADICTION_SCORE_LOW,
) -> list[ValueFinding]:
    """Pair ``final_ending_id`` with the final-week state and flag contradictions."""
    findings: list[ValueFinding] = []
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        ending_id = str(
            run.get("final_ending_id")
            or run.get("last_ending_id")
            or run.get("ending_id")
            or ""
        )
        if not ending_id:
            continue
        log = run.get("weekly_log") or []
        if not log:
            continue
        last_state = _after_state(log[-1])
        if not isinstance(last_state, dict) or not last_state:
            last_state = run.get("final_state") or {}
        money = last_state.get("money") if isinstance(last_state, dict) else None
        stress = last_state.get("stress") if isinstance(last_state, dict) else None
        hunger = last_state.get("hunger") if isinstance(last_state, dict) else None
        academic = (
            last_state.get("academic_progress")
            if isinstance(last_state, dict)
            else None
        )

        def _num(value: Any) -> float | None:
            return float(value) if isinstance(value, (int, float)) else None

        score = 0.0
        score += max(0.0, -(_num(money) or 0.0))
        score += (_num(stress) or 0.0)
        score += (_num(hunger) or 0.0)
        score += max(0.0, 50 - (_num(academic) or 0.0))

        is_success = ending_id.endswith("_success") or ending_id in {
            "scholarship_path",
            "smooth_first_semester",
            "schengen_granted",
        }
        is_failure = ending_id in {"burnout", "cashflow_collapse", "evicted"} or ending_id.startswith(
            "fail"
        )
        if is_success and score >= success_score_high:
            findings.append(
                ValueFinding(
                    finding_id=f"ending_contradiction-{len(findings) + 1:04d}",
                    scope="ending_contradiction",
                    target_id=f"{policy}:{ending_id}",
                    severity="error",
                    metric="contradiction_score",
                    value=round(score, 2),
                    threshold=success_score_high,
                    description=(
                        f"`{ending_id}` reached with score={score:.1f} "
                        f"(≥{success_score_high}). Final state looks broken."
                    ),
                )
            )
        elif is_failure and score <= success_score_low:
            findings.append(
                ValueFinding(
                    finding_id=f"ending_contradiction-{len(findings) + 1:04d}",
                    scope="ending_contradiction",
                    target_id=f"{policy}:{ending_id}",
                    severity="warning",
                    metric="contradiction_score",
                    value=round(score, 2),
                    threshold=success_score_low,
                    description=(
                        f"`{ending_id}` reached with score={score:.1f} "
                        f"(≤{success_score_low}). Final state looks healthy."
                    ),
                )
            )
    return findings


def analyze_route_separation(
    runs: list[dict[str, Any]],
    axes: Sequence[str] = DEFAULT_ROUTE_AXES,
    *,
    distance_warning: float = DEFAULT_ROUTE_DISTANCE_WARNING,
) -> list[ValueFinding]:
    """Measure how far each policy's mean axis is from ``balanced``."""
    findings: list[ValueFinding] = []

    AXIS_STATE_KEY = {
        "academic": "academic_progress",
        "work": "money",
        "social": "social",
        "admin": "visa_progress",
        "slacker": "stress",  # higher is more stressed → less slacker
    }

    def _final_state_of(run: dict[str, Any]) -> dict[str, Any]:
        log = run.get("weekly_log") or []
        if log and isinstance(log[-1], dict):
            last = _after_state(log[-1])
            if last:
                return last
        state = run.get("final_state") or {}
        return state if isinstance(state, dict) else {}

    by_policy: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        policy = str(run.get("policy", "unknown"))
        state = _final_state_of(run)
        for axis in axes:
            key = AXIS_STATE_KEY.get(axis, axis)
            value = state.get(key)
            if isinstance(value, (int, float)):
                by_policy[policy][axis].append(float(value))

    baseline = by_policy.get("balanced") or by_policy.get("balanced ")
    if not baseline:
        return findings
    for policy, axis_values in sorted(by_policy.items()):
        if policy == "balanced":
            continue
        weak: list[str] = []
        for axis in axes:
            ours = axis_values.get(axis, [])
            ref = baseline.get(axis, [])
            if not ours or not ref:
                continue
            ours_mean = sum(ours) / len(ours)
            ref_mean = sum(ref) / len(ref)
            if ref_mean == 0:
                continue
            rel = abs(ours_mean - ref_mean) / max(1.0, abs(ref_mean))
            if rel < distance_warning:
                weak.append(f"{axis}(Δ={rel:.0%})")
        if weak:
            findings.append(
                ValueFinding(
                    finding_id=f"route_distance-{len(findings) + 1:04d}",
                    scope="route",
                    target_id=policy,
                    severity="warning",
                    metric="relative_distance",
                    value=round(distance_warning, 3),
                    threshold=distance_warning,
                    description=(
                        f"Policy `{policy}` differs from `balanced` by < "
                        f"{distance_warning:.0%} on: {', '.join(weak)}."
                    ),
                )
            )
    return findings


def analyze_route_metrics(
    *,
    raw_runs_path: Path | None,
    action_catalog_path: Path | None = None,
    axes: Sequence[str] = DEFAULT_ROUTE_AXES,
) -> dict[str, Any]:
    """Combine all T06 analyses into a single ``route_report.json`` payload."""
    runs: list[dict[str, Any]] = []
    if raw_runs_path is not None and raw_runs_path.exists():
        try:
            runs = [
                json.loads(line)
                for line in raw_runs_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except json.JSONDecodeError:
            runs = []
    action_tags = load_action_tags(raw_runs_path, action_catalog_path)
    groups = analyze_action_groups(runs, action_tags)
    crisis = analyze_crisis_response(runs, action_tags)
    endings = analyze_ending_contradictions(runs)
    routes = analyze_route_separation(runs, axes=axes)

    by_kind: dict[str, int] = defaultdict(int)
    for finding in (*groups, *crisis, *endings, *routes):
        prefix = finding.finding_id.rsplit("-", 1)[0]
        by_kind[prefix] += 1

    return {
        "finding_count": len(groups) + len(crisis) + len(endings) + len(routes),
        "by_kind": dict(sorted(by_kind.items())),
        "axes": list(axes),
        "groups": [f.model_dump(mode="json") for f in groups],
        "crisis_response": [f.model_dump(mode="json") for f in crisis],
        "ending_contradictions": [f.model_dump(mode="json") for f in endings],
        "route_separation": [f.model_dump(mode="json") for f in routes],
        "action_tags_used": dict(sorted(action_tags.items())),
    }


def write_route_report(report: dict[str, Any], path: Path) -> None:
    """Persist the T06 ``route_report.json``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "ACTION_GROUP_KEYWORDS",
    "DEFAULT_CRISIS_RESPONSE_ERROR",
    "DEFAULT_CRISIS_RESPONSE_THRESHOLD",
    "DEFAULT_HUNGER_CRISIS_THRESHOLD",
    "DEFAULT_LOW_MONEY_THRESHOLD",
    "DEFAULT_RECOVERY_GROUP_RATE",
    "DEFAULT_ROUTE_AXES",
    "DEFAULT_ROUTE_DISTANCE_WARNING",
    "DEFAULT_STRESS_CRISIS_THRESHOLD",
    "DEFAULT_STUDY_GROUP_RATE_MIN",
    "DEFAULT_VISA_RISK_THRESHOLD",
    "DEFAULT_WORK_GROUP_RATE_MIN",
    "DEAD_PICK_RATE",
    "DOMINANT_CHOICE_RATE",
    "DOMINANT_PICK_RATE",
    "ENDINGLE_DOMINANCE",
    "analyze_action_groups",
    "analyze_and_write",
    "analyze_crisis_response",
    "analyze_ending_contradictions",
    "analyze_route_metrics",
    "analyze_route_separation",
    "analyze_values",
    "write_route_report",
    "write_value_report",
]
