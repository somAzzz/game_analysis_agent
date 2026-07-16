#!/usr/bin/env python3
"""Serve the bounded Judge API and bundled frontend with the standard library."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from game_analysis_agent.judge_api import (  # noqa: E402
    MAX_REQUEST_BYTES,
    CampaignCreateRequest,
    JudgeAPIError,
    JudgeService,
    ProviderTestRequest,
    parse_json_body,
)
from game_analysis_agent.judge_live_campaign import (  # noqa: E402
    JudgeLiveCampaignError,
    run_judge_live_campaign,
)

CAMPAIGN_ROUTE = re.compile(r"^/api/campaigns/([a-z0-9-]{1,64})$")
EVENTS_ROUTE = re.compile(r"^/api/campaigns/([a-z0-9-]{1,64})/events$")
CANCEL_ROUTE = re.compile(r"^/api/campaigns/([a-z0-9-]{1,64})/cancel$")
EXPERIMENT_ROUTE = re.compile(r"^/api/experiments/([a-z0-9-]{1,64})$")


def handler_factory(service: JudgeService, frontend: Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PlaytestForgeJudge/1"

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            try:
                if path == "/api/provider-status":
                    self._json(HTTPStatus.OK, service.providers.status())
                    return
                if match := CAMPAIGN_ROUTE.fullmatch(path):
                    self._json(HTTPStatus.OK, service.campaigns.get(match.group(1)))
                    return
                if match := EVENTS_ROUTE.fullmatch(path):
                    self._events(service.campaigns.events(match.group(1)))
                    return
                if match := EXPERIMENT_ROUTE.fullmatch(path):
                    self._json(HTTPStatus.OK, service.experiment(match.group(1)))
                    return
                if path.startswith("/api/"):
                    raise JudgeAPIError(
                        "route_not_found", "API route does not exist", "Use the documented API routes.", status_code=404
                    )
                self._static(path)
            except JudgeAPIError as exc:
                self._json(exc.status_code, exc.payload())

        def do_POST(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            try:
                if path == "/api/provider-test":
                    request = parse_json_body(self._body(), ProviderTestRequest)
                    self._json(HTTPStatus.OK, service.providers.test(request))
                    return
                if path == "/api/campaigns":
                    request = parse_json_body(self._body(), CampaignCreateRequest)
                    self._json(HTTPStatus.ACCEPTED, service.campaigns.create(request))
                    return
                if match := CANCEL_ROUTE.fullmatch(path):
                    self._reject_nonempty_body()
                    self._json(HTTPStatus.OK, service.campaigns.cancel(match.group(1)))
                    return
                raise JudgeAPIError(
                    "route_not_found", "API route does not exist", "Use the documented API routes.", status_code=404
                )
            except JudgeAPIError as exc:
                self._json(exc.status_code, exc.payload())

        def _body(self) -> bytes:
            raw = self.headers.get("Content-Length", "0")
            try:
                length = int(raw)
            except ValueError as exc:
                raise JudgeAPIError(
                    "content_length_invalid", "Invalid Content-Length", "Send a bounded JSON request."
                ) from exc
            if length < 0 or length > MAX_REQUEST_BYTES:
                raise JudgeAPIError(
                    "request_too_large", "Request body exceeds 32 KiB", "Send only documented fields.", status_code=413
                )
            return self.rfile.read(length)

        def _reject_nonempty_body(self) -> None:
            if self._body():
                raise JudgeAPIError(
                    "request_invalid", "Cancel does not accept a body", "Send an empty POST request."
                )

        def _json(self, status: int, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _events(self, events: list[dict[str, object]]) -> None:
            body = "".join(
                f"id: {item['sequence']}\nevent: {item['type']}\ndata: {json.dumps(item, sort_keys=True)}\n\n"
                for item in events
            ).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _static(self, request_path: str) -> None:
            relative = request_path.lstrip("/") or "index.html"
            public_prefix = "game_analysis_agent/"
            if relative == public_prefix.rstrip("/"):
                relative = "index.html"
            elif relative.startswith(public_prefix):
                relative = relative.removeprefix(public_prefix) or "index.html"
            candidate = (frontend / relative).resolve()
            if frontend.resolve() not in candidate.parents or not candidate.is_file():
                candidate = frontend / "index.html"
            if not candidate.is_file():
                raise JudgeAPIError(
                    "frontend_unavailable", "Frontend build is unavailable", "Run npm run build.", status_code=404
                )
            body = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print(f"judge-api: {format % args}", file=sys.stderr)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--frontend", type=Path, default=ROOT / "frontend/dist")
    parser.add_argument(
        "--enable-live-openai",
        action="store_true",
        help="Enable the bounded native Godot/OpenAI campaign runner; key remains server-side.",
    )
    args = parser.parse_args()

    runtime_directory: tempfile.TemporaryDirectory[str] | None = None
    if not os.environ.get("GAME_PROJECT_PATH"):
        from game_analysis_agent.build_week_game_pin import prepare_embedded_game_runtime

        runtime_directory = tempfile.TemporaryDirectory(prefix="playtest-forge-game-")
        game_runtime = Path(runtime_directory.name) / "study-in-germany"
        prepare_embedded_game_runtime(ROOT, game_runtime)
        os.environ["GAME_PROJECT_PATH"] = str(game_runtime)

    def live_runner(job):  # noqa: ANN001, ANN202
        try:
            return run_judge_live_campaign(job, project_root=ROOT, environment=os.environ)
        except JudgeLiveCampaignError as exc:
            raise JudgeAPIError(
                "live_campaign_failed",
                str(exc),
                "Inspect the retained campaign evidence; do not relabel it as Replay success.",
                status_code=502,
            ) from exc

    service = JudgeService(
        project_root=ROOT,
        live_runner=live_runner if args.enable_live_openai else None,
    )
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(service, args.frontend.resolve()))
    print(f"Judge API listening on http://{args.host}:{server.server_port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if runtime_directory is not None:
            runtime_directory.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
