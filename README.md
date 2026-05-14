# vLLM Docker: Mistral Nemo Instruct (AWQ)

This repository runs a single **Docker Compose** service: the official **`vllm/vllm-openai`** image, serving **`casperhansen/mistral-nemo-instruct-2407-awq`** with **AWQ** quantization. The server exposes the **OpenAI-compatible HTTP API** on port **8000**.

There is **no** FastAPI gateway, **no** Prometheus/Grafana stack, and **no** auxiliary scripts—only model serving.

## Technology stack

- **Docker** / **Docker Compose**
- **NVIDIA GPU** + drivers + container toolkit (Linux engine; WSL2 on Windows)
- **vLLM** OpenAI server image: `vllm/vllm-openai` (see root [`Dockerfile`](Dockerfile))

## Project layout

| Path | Purpose |
|------|---------|
| [`Dockerfile`](Dockerfile) | Image based on `vllm/vllm-openai`; HF cache env defaults |
| [`docker-compose.yml`](docker-compose.yml) | GPU, volume, `vllm serve` arguments |
| [`.env.example`](.env.example) | Documented optional environment variables (copy to `.env`) |
| [`LICENSE`](LICENSE) | License |

## Prerequisites (Windows + NVIDIA)

- **Docker Desktop** with the **Linux** engine
- **WSL2** with Docker integration enabled
- **NVIDIA Container Toolkit** / GPU support in Docker (e.g. `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`)

If GPU pass-through fails, fix that before building; vLLM requires a CUDA-capable GPU.

## Setup

1. Copy environment template (optional but recommended):

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` if you need a Hugging Face token or different VRAM limits (see below). **If you already have a `.env` from an older setup**, remove or update `VLLM_MAX_MODEL_LEN`, `VLLM_GPU_MEMORY_UTILIZATION`, and `VLLM_MAX_NUM_SEQS`—otherwise those lines **override** the new Compose defaults and you can hit KV-cache or **“free memory … utilization”** errors again.

3. Build and start:

   ```bash
   docker compose up --build
   ```

The API listens at **`http://localhost:8000`**.

The image entrypoint is `vllm serve`; Compose `command:` supplies the model id and flags (do **not** prefix with `vllm` or `serve`).

## Environment variables

Documented in [`.env.example`](.env.example). Common knobs:

| Variable | Role |
|----------|------|
| `HF_TOKEN` | Optional; set if Hub access requires authentication |
| `VLLM_MODEL` | Hugging Face model id (default: `casperhansen/mistral-nemo-instruct-2407-awq`) |
| `VLLM_QUANTIZATION` | Must stay compatible with the checkpoint (default: `awq`) |
| `VLLM_GPU_MEMORY_UTILIZATION` | Fraction of **total** VRAM vLLM targets at startup; must leave headroom for **non-CUDA** use (display, compositor). Default **`0.88`** on Compose; **lower** (e.g. `0.85`) if you see the “Free memory … less than desired GPU memory utilization” error. |
| `VLLM_MAX_MODEL_LEN` | **Context cap** for KV cache sizing. Default **`4096`**, aimed at **~12 GiB** cards (e.g. RTX 4070 Ti). **Lower** (e.g. `512`–`2048`) on **~8 GiB** or if Docker/WSL shows less usable VRAM; **raise** toward `8192` when logs show plenty of KV headroom. |
| `VLLM_MAX_NUM_SEQS` | Max concurrent sequences (default `4`; lower reduces KV pressure). |
| `VLLM_TENSOR_PARALLEL_SIZE` | Tensor parallel degree across GPUs (default `1`) |
| `VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS` | Set `0` (default in Compose) to avoid extra reservation for CUDA graph profiling on small GPUs. |
| `PYTORCH_CUDA_ALLOC_CONF` | PyTorch allocator hint (default `expandable_segments:True`) |

If you previously used a **smaller** model in `.env`, update `VLLM_MODEL` (and possibly `VLLM_MAX_MODEL_LEN`) so you do not accidentally keep serving the old checkpoint.

## Troubleshooting: KV cache / `max_model_len`

If the engine exits with an error like **“KV cache is needed … which is larger than the available KV cache memory”** (or suggests decreasing **`max_model_len`**), your **weights + CUDA graphs** already consume most of the GPU; the configured **`max_model_len`** requires more KV space than is left.

1. **Lower `VLLM_MAX_MODEL_LEN`** in `.env` (the logs often include an **estimated maximum model length** for your card; stay at or below that, or step down from the default `4096` if needed).
2. Keep **`VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=0`** (Compose default) unless you need the profiler; vLLM notes this improves effective KV space on recent versions.

## Troubleshooting: “Free memory … less than desired GPU memory utilization”

vLLM checks that **free** VRAM at engine start is at least **`--gpu-memory-utilization` × total VRAM**. A **desktop GPU** with a display attached often has **~1 GiB** (or more) already reserved, so a high utilization like **`0.92`** can fail even on a **12 GiB** card.

1. **Lower `VLLM_GPU_MEMORY_UTILIZATION`** in `.env` (try **`0.88`** as in the repo default, then **`0.85`** if needed).
2. Close other GPU-heavy apps; on Linux/WSL, reducing compositor or multi-monitor use can reclaim a little VRAM.
3. Only **after** a clean start with headroom, consider **raising** utilization slightly if you need more KV cache—never above what the error message allows.

On **16 GiB+** GPUs you can usually increase **`VLLM_MAX_MODEL_LEN`** (and optionally **`VLLM_MAX_NUM_SEQS`**) after a successful boot.

### Example: RTX 4070 Ti (12 GiB)

With **~12 GiB** total VRAM and this AWQ checkpoint (~8 GiB weights plus graphs/overhead), starting near **`VLLM_MAX_MODEL_LEN=4096`**, **`VLLM_MAX_NUM_SEQS=4`**, and **`VLLM_GPU_MEMORY_UTILIZATION=0.88`** matches the repo defaults ( **`0.88`** leaves room for display-reserved memory). If startup is stable and `nvidia-smi` shows free memory during idle load, you can try **`8192`** context or cautiously **higher** utilization; if vLLM still estimates very small KV space (e.g. in WSL), reduce **`VLLM_MAX_MODEL_LEN`** or **`VLLM_MAX_NUM_SEQS`** per the error message.

### Note: “Port 8000 is already in use, trying port 8001”

You may see the engine worker pick another port for **internal** distributed setup while the **HTTP** API stays on **8000** as configured. That line alone is not necessarily a host port conflict.

## API (OpenAI-compatible)

vLLM exposes routes such as:

- `GET /health` — liveness
- `GET /v1/models` — loaded models
- `POST /v1/chat/completions` — chat completions
- `POST /v1/completions` — text completions
- `GET /metrics` — Prometheus metrics (optional client scrape)

There is **no** API-key middleware in this repo. Add a reverse proxy or API gateway in front if you need authentication.

### Example: chat completion

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"casperhansen/mistral-nemo-instruct-2407-awq\", \"messages\": [{\"role\": \"user\", \"content\": \"Say hello in one sentence.\"}], \"max_tokens\": 64}"
```

Use the same `model` string as returned by `GET /v1/models` if it differs slightly from the Hub id.

## Persistent weights cache

Compose mounts a named volume **`hf-cache`** at `/data/hf` inside the container so repeated starts reuse downloaded weights.

## Testing

- After `docker compose up`, run `curl http://localhost:8000/health` (expect HTTP 200 when ready).
- Run the `curl` example above for an end-to-end generation check.

## Deployment notes

- Pin a specific **`vllm/vllm-openai:<tag>`** in [`Dockerfile`](Dockerfile) instead of `latest` for reproducible production builds.
- Tune `VLLM_MAX_MODEL_LEN` and concurrency for your GPU VRAM; Mistral Nemo AWQ is large and **defaults are conservative** so a first boot succeeds on small GPUs.
- For multi-GPU, increase `VLLM_TENSOR_PARALLEL_SIZE` to match your topology.

## Recent changes

See [`DEVELOPMENT.md`](DEVELOPMENT.md) for the changelog.
