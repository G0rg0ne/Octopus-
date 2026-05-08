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

docker run --rm -it --gpus all -p 8000:8000 ^
  -e HF_HOME=/data/hf ^
  -e HUGGINGFACE_HUB_CACHE=/data/hf/hub ^
  -e TRANSFORMERS_CACHE=/data/hf/transformers ^
  -v hf-cache:/data/hf ^
  octopus-vllm:qwen0.5b ^
  serve Qwen/Qwen2.5-0.5B-Instruct --host 0.0.0.0 --port 8000 --gpu-memory-utilization 0.90 --max-model-len 2048 --max-num-seqs 32
```

Notes:
- The first run will download weights into the mounted cache volume `hf-cache` and will be slower.
- You can override defaults via env vars (see `.env.example`).

## API usage

### Gateway auth
All gateway routes require:
- `X-API-Key: <key>`

Set `API_KEY` in your environment (see `.env.example`).

### Gateway health

```bash
curl -H "X-API-Key: dev-key" http://localhost:8080/health
```

### Gateway: list available models (proxied)

```bash
curl -H "X-API-Key: dev-key" http://localhost:8080/v1/models
```

### Gateway: OpenAI-compatible Completions API (proxied)

```bash
curl -s http://localhost:8080/v1/completions ^
  -H "X-API-Key: dev-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Write a haiku about GPUs.\",\"max_tokens\":64,\"temperature\":0.7}"
```

### Gateway: OpenAI-compatible streaming (SSE passthrough)

```bash
curl -N http://localhost:8080/v1/completions ^
  -H "X-API-Key: dev-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Stream tokens.\",\"max_tokens\":64,\"temperature\":0.7,\"stream\":true}"
```

### Gateway: custom generate (validated)

```bash
curl -s http://localhost:8080/api/v1/generate ^
  -H "X-API-Key: dev-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Say hello.\",\"max_tokens\":32}"
```

### Gateway: custom stream (normalized SSE)

```bash
curl -N http://localhost:8080/api/v1/stream ^
  -H "X-API-Key: dev-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Stream tokens.\",\"max_tokens\":64}"
```

### List available models

```bash
curl http://localhost:8000/v1/models
```

### OpenAI-compatible Completions API (`/v1/completions`)

```bash
curl -s http://localhost:8000/v1/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"Qwen/Qwen2.5-0.5B-Instruct\",\"prompt\":\"Write a haiku about GPUs.\",\"max_tokens\":64,\"temperature\":0.7}"
```

If you prefer, you can also call it with the OpenAI Python client by pointing `base_url` to `http://localhost:8000/v1`.

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
- You can also override serving parameters by editing the `docker run` arguments or the `docker-compose.yml` `command:`.

## Testing / verification checklist
1. `docker version` shows a working server.
2. Start the container via Compose or Docker CLI.
3. `curl http://localhost:8000/v1/models` returns JSON.
4. `curl -X POST http://localhost:8000/v1/completions ...` returns a completion.

## Deployment notes
- For production, pin the base image tag instead of `latest`, and consider configuring:
  - restart policies
  - request limits (`--max-model-len`, `--max-num-seqs`)
  - auth (reverse proxy in front of the OpenAI-compatible server, or use the gateway)

## Recent changes
See `DEVELOPMENT.md`.
