# Development Log

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
