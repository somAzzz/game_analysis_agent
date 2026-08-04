"""Frozen-trace replay and synthetic prefill/decode diagnostics for APC/MTP tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class Endpoint:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 180.0

    @classmethod
    def from_env(cls) -> Endpoint:
        base_url = os.environ.get("VLLM_BASE_URL", "").rstrip("/")
        api_key = os.environ.get("VLLM_API_KEY", "")
        model = os.environ.get("LLM_SERVED_MODEL_NAME", "")
        missing = [
            name
            for name, value in (
                ("VLLM_BASE_URL", base_url),
                ("VLLM_API_KEY", api_key),
                ("LLM_SERVED_MODEL_NAME", model),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"missing endpoint environment: {', '.join(missing)}")
        return cls(base_url=base_url, api_key=api_key, model=model)


def read_trace(
    path: str | Path,
    *,
    phase: str | None = None,
    attempt: int | None = None,
) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [
        row
        for row in rows
        if (phase is None or row["phase"] == phase)
        and (attempt is None or int(row["attempt"]) == attempt)
    ]
    if not selected:
        raise ValueError("trace selection is empty")
    for row in selected:
        canonical = json.dumps(
            row["request"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if actual != row["request_sha256"]:
            raise ValueError(f"trace hash mismatch for {row['request_id']}")
    return selected


def _usage_dict(usage: Any) -> dict[str, int | None]:
    if usage is None:
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def _vllm_request(request: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy frozen traces without changing their verified payload hash."""

    migrated = dict(request)
    if "max_completion_tokens" not in migrated and "max_tokens" in migrated:
        migrated["max_completion_tokens"] = migrated.pop("max_tokens")
    return migrated


def _replay_one(
    client: OpenAI,
    trace: dict[str, Any],
    *,
    pass_id: str,
    concurrency: int,
    ordinal: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = client.chat.completions.create(**_vllm_request(trace["request"]))
        latency_ms = (time.perf_counter() - started) * 1000
        choice = response.choices[0]
        content = str(choice.message.content or "")
        return {
            "schema_version": "inference-ab-request-v1",
            "workload": "frozen_trace",
            "pass": pass_id,
            "concurrency": concurrency,
            "ordinal": ordinal,
            "persona": trace["persona"],
            "seed": trace["seed"],
            "week": trace["week"],
            "phase": trace["phase"],
            "attempt": trace["attempt"],
            "request_sha256": trace["request_sha256"],
            "status": "completed",
            "latency_ms": round(latency_ms, 3),
            "finish_reason": str(choice.finish_reason or ""),
            "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            **_usage_dict(response.usage),
        }
    except Exception as exc:
        return {
            "schema_version": "inference-ab-request-v1",
            "workload": "frozen_trace",
            "pass": pass_id,
            "concurrency": concurrency,
            "ordinal": ordinal,
            "persona": trace["persona"],
            "seed": trace["seed"],
            "week": trace["week"],
            "phase": trace["phase"],
            "attempt": trace["attempt"],
            "request_sha256": trace["request_sha256"],
            "status": "failed",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def replay_trace(
    endpoint: Endpoint,
    *,
    trace_path: str | Path,
    output_path: str | Path,
    concurrency: int,
    passes: tuple[str, ...],
    phase: str | None,
    attempt: int | None,
) -> dict[str, Any]:
    if concurrency not in {1, 4}:
        raise ValueError("frozen trace concurrency must be 1 or 4")
    traces = read_trace(trace_path, phase=phase, attempt=attempt)
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for ordinal, row in enumerate(traces, 1):
        grouped[str(row["persona"])].append((ordinal, row))
    client = OpenAI(
        base_url=endpoint.base_url,
        api_key=endpoint.api_key,
        timeout=endpoint.timeout_seconds,
        max_retries=0,
    )
    all_rows: list[dict[str, Any]] = []
    pass_summaries = []
    for pass_id in passes:
        pass_started = time.perf_counter()

        def run_persona(
            items: list[tuple[int, dict[str, Any]]],
            bound_pass_id: str = pass_id,
        ) -> list[dict[str, Any]]:
            return [
                _replay_one(
                    client,
                    trace,
                    pass_id=bound_pass_id,
                    concurrency=concurrency,
                    ordinal=ordinal,
                )
                for ordinal, trace in items
            ]

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(run_persona, items) for items in grouped.values()]
            pass_rows = [row for future in futures for row in future.result()]
        pass_rows.sort(key=lambda row: int(row["ordinal"]))
        all_rows.extend(pass_rows)
        pass_summaries.append(
            {
                "pass": pass_id,
                "wall_time_seconds": round(time.perf_counter() - pass_started, 6),
                "requests": len(pass_rows),
                "failed": sum(row["status"] != "completed" for row in pass_rows),
                "prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in pass_rows),
                "completion_tokens": sum(
                    int(row.get("completion_tokens") or 0) for row in pass_rows
                ),
            }
        )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in all_rows),
        encoding="utf-8",
    )
    summary = {
        "schema_version": "inference-ab-replay-summary-v1",
        "trace_path": str(trace_path),
        "trace_sha256": hashlib.sha256(Path(trace_path).read_bytes()).hexdigest(),
        "selection": {"phase": phase, "attempt": attempt},
        "concurrency": concurrency,
        "passes": pass_summaries,
        "records": len(all_rows),
        "failed": sum(row["status"] != "completed" for row in all_rows),
    }
    destination.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if summary["failed"]:
        raise RuntimeError(f"frozen trace replay had {summary['failed']} failed requests")
    return summary


def _tokenize(endpoint: Endpoint, messages: list[dict[str, str]]) -> int:
    url = endpoint.base_url.rsplit("/v1", 1)[0] + "/tokenize"
    payload = json.dumps(
        {
            "model": endpoint.model,
            "messages": messages,
            "chat_template_kwargs": {"enable_thinking": False},
        }
    ).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {endpoint.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=endpoint.timeout_seconds) as response:
        value = json.load(response)
    return int(value["count"])


def calibrated_messages(endpoint: Endpoint, target_tokens: int) -> list[dict[str, str]]:
    low, high = 0, target_tokens * 2
    best: tuple[int, list[dict[str, str]]] | None = None
    while low <= high:
        repeats = (low + high) // 2
        messages = [{"role": "user", "content": "x" + " x" * repeats}]
        count = _tokenize(endpoint, messages)
        if best is None or abs(count - target_tokens) < abs(best[0] - target_tokens):
            best = (count, messages)
        if count < target_tokens:
            low = repeats + 1
        elif count > target_tokens:
            high = repeats - 1
        else:
            return messages
    assert best is not None
    raise RuntimeError(
        f"could not calibrate exact prompt length {target_tokens}; closest was {best[0]}"
    )


def _diagnostic_one(
    client: OpenAI,
    endpoint: Endpoint,
    *,
    messages: list[dict[str, str]],
    prompt_target: int,
    output_target: int,
    concurrency: int,
    ordinal: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    first_token_s: float | None = None
    usage = None
    digest = hashlib.sha256()
    try:
        stream = client.chat.completions.create(
            model=endpoint.model,
            messages=messages,
            temperature=0.0,
            max_completion_tokens=output_target,
            stream=True,
            stream_options={"include_usage": True},
            extra_body={
                "ignore_eos": True,
                "seed": 42,
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        for chunk in stream:
            if getattr(chunk, "usage", None) is not None:
                usage = chunk.usage
            for choice in getattr(chunk, "choices", []):
                delta = getattr(choice, "delta", None)
                content = str(getattr(delta, "content", None) or "")
                reasoning = str(
                    getattr(delta, "reasoning", None)
                    or getattr(delta, "reasoning_content", None)
                    or ""
                )
                token_text = content + reasoning
                if token_text:
                    if first_token_s is None:
                        first_token_s = time.perf_counter()
                    digest.update(token_text.encode("utf-8"))
        completed = time.perf_counter()
        usage_values = _usage_dict(usage)
        completion_tokens = int(usage_values["completion_tokens"] or 0)
        ttft_ms = (first_token_s - started) * 1000 if first_token_s is not None else math.nan
        e2e_ms = (completed - started) * 1000
        tpot_ms = (
            (e2e_ms - ttft_ms) / max(1, completion_tokens - 1)
            if first_token_s is not None
            else math.nan
        )
        return {
            "schema_version": "inference-ab-request-v1",
            "workload": "diagnostic",
            "prompt_target": prompt_target,
            "output_target": output_target,
            "concurrency": concurrency,
            "ordinal": ordinal,
            "status": "completed",
            "ttft_ms": round(ttft_ms, 3),
            "tpot_ms": round(tpot_ms, 3),
            "e2e_latency_ms": round(e2e_ms, 3),
            "response_sha256": digest.hexdigest(),
            **usage_values,
        }
    except Exception as exc:
        return {
            "schema_version": "inference-ab-request-v1",
            "workload": "diagnostic",
            "prompt_target": prompt_target,
            "output_target": output_target,
            "concurrency": concurrency,
            "ordinal": ordinal,
            "status": "failed",
            "e2e_latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_diagnostics(
    endpoint: Endpoint,
    *,
    output_path: str | Path,
    prompt_tokens: tuple[int, ...],
    output_tokens: tuple[int, ...],
    concurrencies: tuple[int, ...],
    requests_per_cell: int,
) -> dict[str, Any]:
    client = OpenAI(
        base_url=endpoint.base_url,
        api_key=endpoint.api_key,
        timeout=endpoint.timeout_seconds,
        max_retries=0,
    )
    prompts = {target: calibrated_messages(endpoint, target) for target in prompt_tokens}
    rows: list[dict[str, Any]] = []
    cells = []
    for concurrency in concurrencies:
        for prompt_target in prompt_tokens:
            for output_target in output_tokens:
                started = time.perf_counter()
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    futures = [
                        pool.submit(
                            _diagnostic_one,
                            client,
                            endpoint,
                            messages=prompts[prompt_target],
                            prompt_target=prompt_target,
                            output_target=output_target,
                            concurrency=concurrency,
                            ordinal=ordinal,
                        )
                        for ordinal in range(1, requests_per_cell + 1)
                    ]
                    cell_rows = [future.result() for future in as_completed(futures)]
                cell_rows.sort(key=lambda row: int(row["ordinal"]))
                rows.extend(cell_rows)
                completed = [row for row in cell_rows if row["status"] == "completed"]
                cells.append(
                    {
                        "prompt_target": prompt_target,
                        "output_target": output_target,
                        "concurrency": concurrency,
                        "wall_time_seconds": round(time.perf_counter() - started, 6),
                        "requests": len(cell_rows),
                        "failed": len(cell_rows) - len(completed),
                        "median_ttft_ms": round(
                            statistics.median(float(row["ttft_ms"]) for row in completed), 3
                        )
                        if completed
                        else None,
                        "median_tpot_ms": round(
                            statistics.median(float(row["tpot_ms"]) for row in completed), 3
                        )
                        if completed
                        else None,
                    }
                )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = {
        "schema_version": "inference-ab-diagnostic-summary-v1",
        "records": len(rows),
        "failed": sum(row["status"] != "completed" for row in rows),
        "cells": cells,
    }
    destination.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if summary["failed"]:
        raise RuntimeError(f"diagnostic sweep had {summary['failed']} failed requests")
    return summary


def _csv_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item) for item in value.split(",") if item)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    replay = subparsers.add_parser("replay")
    replay.add_argument("--trace", type=Path, required=True)
    replay.add_argument("--output", type=Path, required=True)
    replay.add_argument("--concurrency", type=int, choices=(1, 4), required=True)
    replay.add_argument("--passes", default="cold,warm")
    replay.add_argument("--phase")
    replay.add_argument("--attempt", type=int)
    diagnostic = subparsers.add_parser("diagnostic")
    diagnostic.add_argument("--output", type=Path, required=True)
    diagnostic.add_argument("--prompt-tokens", default="512,2048,4096")
    diagnostic.add_argument("--output-tokens", default="32,96,256,768")
    diagnostic.add_argument("--concurrency", default="1,4")
    diagnostic.add_argument("--requests-per-cell", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    endpoint = Endpoint.from_env()
    if args.command == "replay":
        summary = replay_trace(
            endpoint,
            trace_path=args.trace,
            output_path=args.output,
            concurrency=args.concurrency,
            passes=tuple(item for item in args.passes.split(",") if item),
            phase=args.phase,
            attempt=args.attempt,
        )
    else:
        summary = run_diagnostics(
            endpoint,
            output_path=args.output,
            prompt_tokens=_csv_ints(args.prompt_tokens),
            output_tokens=_csv_ints(args.output_tokens),
            concurrencies=_csv_ints(args.concurrency),
            requests_per_cell=args.requests_per_cell,
        )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
