# Base image for the game-analysis-agent (Python 3.12, slim).
# Only the runtime libs we need; no GPU driver required here — the vLLM
# container carries the GPU driver / CUDA stack separately and exposes
# its OpenAI-compatible HTTP endpoint on `vllm:8000`.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    # The agent talks to vLLM via http://vllm:8000/v1 by default;
    # both paths below default to that so `docker compose run agent`
    # "just works" without exporting extra env. Override per call via
    # `docker compose run -e VLLM_BASE_URL=... agent`.
    VLLM_BASE_URL=http://vllm:8000/v1 \
    VLLM_API_KEY=local-dev-token \
    LLM_SERVED_MODEL_NAME=qwen3.6-27b-nvfp4 \
    GAME_PROJECT_PATH=/app/demo/study-in-germany

WORKDIR /app

# Build deps for pyyaml / pydantic; runtime image only needs them as wheels,
# but the slim base misses a couple of headers for a small minority of CI
# setups. Keep this lean.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      tini \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first so the layer is reused on code changes.
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip \
 && pip install . \
 && pip install --no-cache-dir openai pydantic pyyaml

# Now copy the source. Done in two steps so Docker caches the pip layer.
COPY src/ ./src/
COPY tools/ ./tools/
COPY prompts/ ./prompts/
COPY scripts/tools ./scripts/tools/
COPY config/ ./config/
COPY demo/ ./demo/
COPY docs/ ./docs/

# Ensure the package is importable when invoked with `python -m`.
ENV PYTHONPATH=/app/src

# `tini` reaps zombies and forwards signals properly — matters when the
# CLI is wired into container shutdown.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default to the orchestration CLI's help screen so `docker run` does
# something useful; override per-call by appending subcommands:
#   docker compose run agent sim --runs 100 --policy balanced
CMD ["python", "tools/run_gameplay_agent.py", "--help"]
