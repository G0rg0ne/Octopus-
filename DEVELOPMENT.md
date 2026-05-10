# Development Log

## [2026-05-10 15:47] - FEATURE

### Changes
- Added Prometheus metrics to the FastAPI gateway (wrapper) and exposed `GET /metrics`.
- Added Prometheus scraping for the gateway (`job_name: api`) so Grafana can chart wrapper success/error rates.
- Extended the vLLM Grafana dashboard with wrapper panels for inference success rate, error rate, and error-type breakdown.

### Files Modified
- `backend/requirements.txt`
- `backend/app/main.py`
- `backend/app/core/metrics.py`
- `observability/prometheus/prometheus.yml`
- `observability/grafana/dashboards/vllm_latency_throughput.json`
- `README.md`

### Rationale
We need visibility into failures that occur in the gateway before a request reaches vLLM (auth, validation, wrong content-type, malformed JSON), and to distinguish those from upstream unavailability.

### Breaking Changes
None

### Next Steps
- Optionally add a Grafana variable for the wrapper `job` label (currently hardcoded to `job="api"` in the new panels).

## [2026-05-09 15:38] - BUGFIX

### Changes
- Fixed Grafana dashboard PromQL to use vLLM’s exported counter names (`*_total`) so panels like **Requests / sec** and token throughput populate.
- Updated `README.md` with an Observability section describing the Prometheus + Grafana stack and the dashboard location.

### Files Modified
- `observability/grafana/dashboards/vllm_latency_throughput.json`
- `README.md`

### Rationale
The vLLM `/metrics` endpoint exports counters such as `vllm:request_success_total`, but the dashboard referenced non-existent series names (without the `_total` suffix), resulting in “No data” despite successful scrapes.

### Breaking Changes
None

### Next Steps
- Consider adjusting KV cache panels to use `max_over_time(vllm:kv_cache_usage_perc[5m])` if you want to visualize peaks rather than instantaneous values.

## [2026-05-09 15:56] - CONFIG

### Changes
- Tuned vLLM Compose defaults to reduce CUDA OOM risk by lowering `--gpu-memory-utilization`, `--max-model-len`, and `--max-num-seqs`.
- Made vLLM serving parameters configurable via `.env` with sane defaults and added `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` to reduce allocator fragmentation.
- Added `.env.example` documenting supported environment variables (no secrets).
- Updated `README.md` to reflect the new defaults and document the additional vLLM env knobs.

### Files Modified
- `docker-compose.yml`
- `.env.example`
- `README.md`
- `DEVELOPMENT.md`

### Rationale
vLLM allocates KV cache during engine initialization based on concurrency and context limits; the previous defaults could exceed available VRAM on 12GB GPUs or when the GPU is already partially in use. Making these knobs configurable improves reliability across different GPUs.

### Breaking Changes
None (defaults changed only; you can restore prior settings via `.env`).

### Next Steps
- If you still see OOM, reduce `VLLM_MAX_NUM_SEQS` further (e.g. 4) and/or `VLLM_MAX_MODEL_LEN` (e.g. 512), and ensure nothing else is using the GPU.

## [2026-05-09 15:45] - DOCS

### Changes
- Standardized `README.md` on **bash**: `\` line continuations everywhere, `export GATEWAY` / `VLLM` / `API_KEY` session setup, and all gateway or direct `curl` examples using those variables.
- Replaced Windows CMD `^` continuations (including Docker CLI `docker run` example) with bash syntax.
- Expanded direct vLLM section with **streaming** completions and **chat** completions (non-stream + stream) examples; aligned gateway chat examples with subheadings.
- Updated testing checklist to use the same bash exports and variable-based curls.

### Files Modified
- `README.md`
- `DEVELOPMENT.md`

### Rationale
Examples should paste cleanly into Git Bash, WSL, and Linux terminals without shell-specific continuations.

### Breaking Changes
None

### Next Steps
None

## [2026-05-09 14:30] - DOCS

### Changes
- Documented that README multi-line `curl` examples use **`^`** for **cmd.exe** only; Git Bash/WSL/bash must use **`\`** or a one-line command. Explained how mis-pasted `^` leads to missing headers and `Invalid or missing API key`, plus `Could not resolve host: ^` / `-H: command not found`.
- Added a shell continuation table and a cross-shell one-line streaming `curl` example.

### Files Modified
- `README.md`
- `DEVELOPMENT.md`

### Rationale
Users running examples from Git Bash hit confusing errors; clarify shell-specific line endings.

### Breaking Changes
None

### Next Steps
None

## [2026-05-09 12:00] - DOCS

### Changes
- Expanded `README.md` API section into a full endpoint reference: gateway vs direct vLLM, auth notes (including optional health key), and per-route descriptions with example `curl` commands for health, models, completions, chat completions (non-stream and SSE), `/api/v1/generate`, and `/api/v1/stream`.
- Clarified that OpenAI-compatible completion routes are **POST** only and noted **405** on **GET**.
- Extended the testing checklist with gateway smoke checks.

### Files Modified
- `README.md`
- `DEVELOPMENT.md`

### Rationale
Make every exposed route easy to discover with a one-line purpose and a copy-paste example.

### Breaking Changes
None

### Next Steps
None

## [2026-05-08 20:55] - FEATURE

### Changes
- Added a Docker image based on `vllm/vllm-openai` to serve `Qwen/Qwen2.5-0.5B-Instruct` using `vllm serve`.
- Added optional `docker-compose.yml` with NVIDIA GPU reservation and a persistent Hugging Face cache volume.
- Added helper run scripts for Windows PowerShell and bash.
- Documented how to call the OpenAI-compatible `/v1/completions` endpoint and explained engine startup, weights loading, and KV cache/GPU memory knobs.

### Files Modified
- `Dockerfile`
- `docker-compose.yml`
- `scripts/run_vllm.ps1`
- `scripts/run_vllm.sh`
- `README.md`
- `DEVELOPMENT.md`
- `.env.example`

### Rationale
Make local GPU serving reproducible and easy to validate via OpenAI-compatible HTTP endpoints while keeping image size smaller by downloading model weights at runtime and caching them on a volume.

### Breaking Changes
None

### Next Steps
- Pin a specific `vllm/vllm-openai` base image tag once your environment is stable.
- If you want to use gated models, provide `HF_TOKEN` via environment variables (never commit it).

## [2026-05-08 21:13] - BUGFIX

### Changes
- Removed the `CMD ["bash", "-lc", ...]` from the `Dockerfile` because the base image `ENTRYPOINT` caused the args to be passed to the `vllm` CLI (breaking startup).
- Updated Docker CLI instructions, Compose `command`, and run scripts to pass `serve ...` arguments explicitly.

### Files Modified
- `Dockerfile`
- `docker-compose.yml`
- `scripts/run_vllm.ps1`
- `scripts/run_vllm.sh`
- `README.md`

### Rationale
Fix container startup by aligning with the base image’s entrypoint behavior and avoiding shell flags being interpreted as `vllm` arguments.

### Breaking Changes
None

### Next Steps
- Rebuild the image and run `curl http://localhost:8000/v1/models` to confirm the server is up.

## [2026-05-08 22:58] - FEATURE

### Changes
- Added a FastAPI gateway service that wraps the vLLM OpenAI server with API-key auth, request logging (structlog), a `/health` endpoint, and streaming support (SSE passthrough + normalized SSE for a custom stream route).
- Added custom validated endpoints under `/api/v1` (`/api/v1/generate`, `/api/v1/stream`) and OpenAI-compatible proxy routes (`/v1/models`, `/v1/completions`, `/v1/chat/completions`).
- Updated Compose to run the gateway as a sidecar container on port 8080.
- Added a repo `.env.example` including gateway configuration.

### Files Modified
- `docker-compose.yml`
- `README.md`
- `.env.example`
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/core/security.py`
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/endpoints/health.py`
- `backend/app/api/v1/endpoints/openai_proxy.py`
- `backend/app/api/v1/endpoints/generate.py`
- `backend/app/schemas/generate.py`

### Rationale
Provide a thin, async HTTP gateway in front of vLLM for practical production concerns (auth, logging, health checks) while keeping vLLM responsible for scheduling/continuous batching and token generation.

### Breaking Changes
`docker compose up --build` now exposes the recommended client entrypoint on `http://localhost:8080` (gateway). The direct vLLM server remains available on `http://localhost:8000`.

### Next Steps
- Optionally disable `/v1/chat/completions` proxy if your chosen vLLM server build doesn't enable it.
- Add automated tests for auth, health, and streaming behavior.

## [2026-05-08 23:36] - BUGFIX

### Changes
- Fixed the Compose `vllm` service `command` to match the image entrypoint behavior (this image uses `ENTRYPOINT ["vllm","serve"]`), so Compose now passes only `<model> ...` arguments (no leading `vllm` or `serve`).

### Files Modified
- `docker-compose.yml`
- `README.md`
- `DEVELOPMENT.md`

### Rationale
This image already runs `vllm serve` via its entrypoint. Including `serve` again in `command:` resulted in `vllm serve serve <model> ...`, which caused `vllm: error: unrecognized arguments: <model>`.

### Breaking Changes
None

### Next Steps
- Rebuild and restart the `vllm` service, then confirm `curl http://localhost:8000/v1/models` returns JSON.
