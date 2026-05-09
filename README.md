# vLLM Docker Serve + FastAPI Gateway (Qwen2.5-0.5B)

This repo provides:
- a **Dockerized vLLM OpenAI-compatible server** for a small model: **`Qwen/Qwen2.5-0.5B-Instruct`**, and
- a **FastAPI gateway** that wraps vLLM with **API-key auth**, **request logging (structlog)**, **SSE streaming**, **input validation**, and a **`/health`** route.

It focuses on:
- Serving with `vllm serve`
- Calling the OpenAI-compatible **`/v1/completions`** endpoint
- Understanding startup phases: **engine init**, **weights loading**, **KV cache / GPU memory allocation**

## Tech stack
- **Docker Desktop** (Windows)
- **NVIDIA GPU** + NVIDIA drivers + WSL2 integration
- **vLLM OpenAI server image**: `vllm/vllm-openai` (base image)
- **FastAPI** + **uvicorn**
- **httpx** (async proxy)
- **structlog** (JSON request logs)

## Project structure
- `Dockerfile`: builds the serving image (runtime downloads model weights)
- `docker-compose.yml`: optional Compose setup with GPU + persistent Hugging Face cache volume
- `backend/`: FastAPI gateway service (sidecar container)
- `scripts/run_vllm.ps1`: build + run (Windows PowerShell)
- `scripts/run_vllm.sh`: build + run (bash)
- `.env.example`: optional environment variables (no secrets)

## Prerequisites (Windows + NVIDIA GPU)
You need all of the following before the container can start successfully:
- **Docker Desktop running** with the **Linux engine** enabled
  - A quick check is `docker version` (should show both client + server).
- **WSL2 enabled** and Docker Desktop WSL integration on.
- **NVIDIA Container Toolkit support** in Docker Desktop (GPU pass-through works)
  - Quick check once Docker is up: `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`

If `docker build` fails with a message about `dockerDesktopLinuxEngine` not found, start Docker Desktop and ensure the Linux engine context is healthy.

## Build + run

### Option A: Docker Compose

```bash
docker compose up --build
```

This brings up:
- **Gateway**: `http://localhost:8080`
- **vLLM (direct)**: `http://localhost:8000`

Notes:
- The vLLM image in this repo inherits an entrypoint of `vllm serve`, so Compose passes `command:` as `<model> ...` (do not prefix the command with `vllm` or `serve`).

### Option B: Docker CLI

```bash
docker build -t octopus-vllm:qwen0.5b .

docker run --rm -it --gpus all -p 8000:8000 \
  -e HF_HOME=/data/hf \
  -e HUGGINGFACE_HUB_CACHE=/data/hf/hub \
  -e TRANSFORMERS_CACHE=/data/hf/transformers \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  -v hf-cache:/data/hf \
  octopus-vllm:qwen0.5b \
  serve Qwen/Qwen2.5-0.5B-Instruct --host 0.0.0.0 --port 8000 --gpu-memory-utilization 0.55 --max-model-len 1024 --max-num-seqs 8
```

Notes:
- The first run will download weights into the mounted cache volume `hf-cache` and will be slower.
- You can override defaults via env vars (see `.env.example`).

## API reference

Two HTTP fronts:

| Base URL | Role |
|----------|------|
| `http://localhost:8080` | **Gateway** (Compose): API-key auth on most routes, proxies to vLLM |
| `http://localhost:8000` | **vLLM** directly: same OpenAI-compatible paths, no gateway auth |

Replace hosts/ports if you run services differently.

### Bash session setup

All gateway examples below use these variables. Defaults match `docker compose` (`API_KEY` / `dev-key`). Change them if your gateway URL or API key differs.

```bash
export GATEWAY=http://localhost:8080
export VLLM=http://localhost:8000
export API_KEY=dev-key
```

Multi-line commands use **`\`** at the end of each line (bash / Git Bash / WSL). Each snippet is valid bash when pasted after the exports.

### Gateway authentication

Most gateway routes require:

- Header: `X-API-Key: <key>` (must match `API_KEY`, default `dev-key` in Compose).

Exceptions:

- **`GET /health`** does not require a key unless you set `REQUIRE_API_KEY_ON_HEALTH=true`.

OpenAI-compatible completion routes accept **`POST` only** (a **`GET`** returns **405**).

---

### Gateway (`$GATEWAY`)

Requires [session setup](#bash-session-setup). Uses `$API_KEY` for protected routes.

#### `GET /health`

Checks gateway availability and whether vLLM responds by requesting upstream `GET /v1/models`. Returns JSON with `status` and upstream latency. No API key unless `REQUIRE_API_KEY_ON_HEALTH=true`.

```bash
curl -s "${GATEWAY}/health"
```

#### `GET /v1/models`

Lists models from vLLM (proxied JSON). Same shape as the OpenAI-compatible models listing.

```bash
curl -s \
  -H "X-API-Key: ${API_KEY}" \
  "${GATEWAY}/v1/models"
```

#### `POST /v1/completions`

OpenAI-compatible **text completions**. Body must be **`Content-Type: application/json`**. Non-streaming: omit `stream` or set `"stream": false`; response is one JSON object when generation finishes.

```bash
curl -s -X POST "${GATEWAY}/v1/completions" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Write a haiku about GPUs.\",\"max_tokens\":64,\"temperature\":0.7}"
```

Streaming: set `"stream": true`; gateway returns **SSE** (`text/event-stream`) passthrough from vLLM. Use `curl -N` so chunks arrive as they are generated.

```bash
curl -N -X POST "${GATEWAY}/v1/completions" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Stream tokens.\",\"max_tokens\":64,\"temperature\":0.7,\"stream\":true}"
```

#### `POST /v1/chat/completions`

OpenAI-compatible **chat** API (`messages` array). Proxied like completions; use `"stream": true` for SSE streaming.

Non-streaming:

```bash
curl -s -X POST "${GATEWAY}/v1/chat/completions" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in one sentence.\"}],\"max_tokens\":64}"
```

Streaming:

```bash
curl -N -X POST "${GATEWAY}/v1/chat/completions" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"Count to three slowly.\"}],\"max_tokens\":64,\"stream\":true}"
```

#### `POST /api/v1/generate`

Gateway-native endpoint: **validated** request body (Pydantic), calls upstream completions **non-streaming**, returns a **normalized** JSON body (`text`, `finish_reason`, `usage`, etc.) instead of raw OpenAI shapes.

```bash
curl -s -X POST "${GATEWAY}/api/v1/generate" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Say hello.\",\"max_tokens\":32}"
```

#### `POST /api/v1/stream`

Same validated input as `/api/v1/generate`, but streams **normalized SSE**: `event: token` lines with JSON `{"text":"..."}`, then `event: done`. Easier to consume than raw OpenAI SSE if you only need incremental text.

```bash
curl -N -X POST "${GATEWAY}/api/v1/stream" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Stream tokens.\",\"max_tokens\":64}"
```

---

### Direct vLLM (`$VLLM`)

Requires [session setup](#bash-session-setup) for `$VLLM` (no API key on these routes). Same OpenAI-style paths as upstream vLLM.

#### `GET /v1/models`

```bash
curl -s "${VLLM}/v1/models"
```

#### `POST /v1/completions`

Non-streaming:

```bash
curl -s -X POST "${VLLM}/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Write a haiku about GPUs.\",\"max_tokens\":64,\"temperature\":0.7}"
```

Streaming (`stream: true`, OpenAI SSE):

```bash
curl -N -X POST "${VLLM}/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Stream tokens.\",\"max_tokens\":64,\"temperature\":0.7,\"stream\":true}"
```

#### `POST /v1/chat/completions`

Available when your vLLM build exposes chat completions.

Non-streaming:

```bash
curl -s -X POST "${VLLM}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in one sentence.\"}],\"max_tokens\":64}"
```

Streaming:

```bash
curl -N -X POST "${VLLM}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"Count to three slowly.\"}],\"max_tokens\":64,\"stream\":true}"
```

You can use the official OpenAI Python client with `base_url` set to `http://localhost:8000/v1` (direct) or `http://localhost:8080/v1` (gateway; add default header `X-API-Key`).

## Concepts (what you’ll see in logs)

### Engine startup
When `vllm serve` starts, it initializes:
- the HTTP server (OpenAI-compatible routes like `/v1/completions`), and
- the vLLM engine/scheduler + CUDA runtime context(s).

### Model weights loading
On the **first startup**, Hugging Face files are downloaded into the cache directory (mounted volume). Then the model weights are loaded and prepared for inference. Subsequent starts reuse the cache and are typically much faster.

### GPU memory allocation (KV cache)
vLLM uses GPU memory for:
- **model weights**
- **temporary buffers/activations** (peak during prompt “prefill”)
- **KV cache** (dominates for long contexts and/or high concurrency)

Key knobs (wired in `Dockerfile` and overridable via env vars):
- `--gpu-memory-utilization`: fraction of GPU memory available for vLLM-managed allocations; vLLM derives KV cache size from this unless you set a fixed KV cache size.
- `--max-model-len`: upper bound on context length; longer contexts require more KV cache.
- `--max-num-seqs`: upper bound on concurrent sequences; higher concurrency increases KV cache demand.

If you see OOM errors, reduce `VLLM_GPU_MEMORY_UTILIZATION`, `VLLM_MAX_MODEL_LEN`, and/or `VLLM_MAX_NUM_SEQS`.

## Environment variables
- `HF_TOKEN` (optional): only required for gated Hugging Face models.
- vLLM serving knobs (Compose defaults are in `.env.example`):
  - `VLLM_GPU_MEMORY_UTILIZATION`
  - `VLLM_MAX_MODEL_LEN`
  - `VLLM_MAX_NUM_SEQS`
  - `PYTORCH_CUDA_ALLOC_CONF` (recommended: `expandable_segments:True`)
- You can also override serving parameters by editing the `docker run` arguments or the `docker-compose.yml` `command:`.

## Testing / verification checklist

After `docker compose up --build`, in bash:

```bash
export GATEWAY=http://localhost:8080 VLLM=http://localhost:8000 API_KEY=dev-key
```

1. `docker version` shows a working server.
2. Compose (or Docker CLI) has started vLLM and the gateway.
3. `curl -s "${VLLM}/v1/models"` returns JSON.
4. `curl -s -X POST "${VLLM}/v1/completions" -H "Content-Type: application/json" -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Hi\",\"max_tokens\":8}"` returns a completion.
5. `curl -s "${GATEWAY}/health"` returns `"status":"ok"` when vLLM is ready.
6. `curl -s -H "X-API-Key: ${API_KEY}" "${GATEWAY}/v1/models"` returns JSON.

## Deployment notes
- For production, pin the base image tag instead of `latest`, and consider configuring:
  - restart policies
  - request limits (`--max-model-len`, `--max-num-seqs`)
  - auth (reverse proxy in front of the OpenAI-compatible server, or use the gateway)

## Recent changes
See `DEVELOPMENT.md`.
