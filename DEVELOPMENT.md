# Development log

## [2026-05-14 12:00] - REFACTOR

### Changes

- Reduced the repository to **vLLM-only** Docker Compose: one service serving `casperhansen/mistral-nemo-instruct-2407-awq` with `--quantization awq`.
- Removed the FastAPI gateway, Prometheus, Grafana, and helper scripts.
- Added [`.env.example`](.env.example) with serving-related variables.
- Rewrote [`README.md`](README.md) for the new scope.

### Files modified

- [`docker-compose.yml`](docker-compose.yml)
- [`Dockerfile`](Dockerfile)
- [`README.md`](README.md)
- [`.env.example`](.env.example)
- [`DEVELOPMENT.md`](DEVELOPMENT.md) (this file)

### Files / directories removed

- `backend/` (FastAPI gateway)
- `observability/` (Prometheus + Grafana)
- `scripts/` (`run_vllm.sh`, `run_vllm.ps1`, `stress_test_gateway.sh`)

### Rationale

The goal was **only** OpenAI-compatible model hosting with no sidecar API or observability stack, using the Mistral Nemo AWQ checkpoint from Hugging Face.

### Breaking changes

- **Port 8080** FastAPI gateway is **gone**; clients must use **port 8000** on the vLLM container directly.
- **API-key auth** and gateway-specific metrics no longer exist; use an external proxy if needed.
- **Prometheus/Grafana** configs were removed; scrape `http://localhost:8000/metrics` from your own monitoring if required.

### Next steps

- Pin a concrete `vllm/vllm-openai` image tag in production.
- Adjust `VLLM_MAX_MODEL_LEN` / `VLLM_GPU_MEMORY_UTILIZATION` per GPU after smoke tests.

## [2026-05-14 22:00] - CONFIG

### Changes

- Tightened default serving parameters so vLLM can start on **low-VRAM** GPUs with Mistral Nemo AWQ: lower default `max_model_len`, lower `max_num_seqs`, slightly higher `gpu_memory_utilization`, and `VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=0` in Compose.
- Documented KV-cache errors and tuning in [`README.md`](README.md).

### Files modified

- [`docker-compose.yml`](docker-compose.yml)
- [`Dockerfile`](Dockerfile)
- [`.env.example`](.env.example)
- [`README.md`](README.md)
- [`DEVELOPMENT.md`](DEVELOPMENT.md) (this file)

### Rationale

A run on a small GPU failed with insufficient KV cache for `max_model_len=8192` while weights already used most VRAM; vLLM estimated ~560 tokens of headroom. Conservative defaults plus disabling CUDA graph memory profiling improve first-boot success; operators with more VRAM should raise `VLLM_MAX_MODEL_LEN` in `.env`.

### Breaking changes

- Default **`VLLM_MAX_MODEL_LEN`** in Compose dropped from `8192` to **`512`**. Set a higher value in `.env` if your GPU has capacity.

### Next steps

- After a stable boot, increase `VLLM_MAX_MODEL_LEN` gradually and watch for OOM.

## [2026-05-14 23:45] - CONFIG

### Changes

- Raised default **`VLLM_MAX_MODEL_LEN`** to **4096** and **`VLLM_MAX_NUM_SEQS`** to **4** in Compose/Dockerfile for **~12 GiB** GPUs (e.g. RTX 4070 Ti); recreated [`.env.example`](.env.example) with matching values and comments for 8 GiB vs 12 GiB tuning.
- README: table updates and an **RTX 4070 Ti (12 GiB)** subsection with guidance to try `8192` when stable.

### Files modified

- [`docker-compose.yml`](docker-compose.yml)
- [`Dockerfile`](Dockerfile)
- [`.env.example`](.env.example)
- [`README.md`](README.md)
- [`DEVELOPMENT.md`](DEVELOPMENT.md) (this file)

### Rationale

`nvidia-smi` on the target machine shows **RTX 4070 Ti / 12282 MiB**; defaults of `512`/`2` are unnecessarily small for that class. **4096**/`4` is a better default while keeping troubleshooting for low-VRAM and WSL edge cases.

### Breaking changes

- Default **`VLLM_MAX_MODEL_LEN`** increased from **`512`** to **`4096`**; **`VLLM_MAX_NUM_SEQS`** from **`2`** to **`4`**. Machines with **~8 GiB** effective VRAM should set lower values in `.env`.

### Next steps

- If `8192` is desired on 12 GiB, test incrementally after a clean boot.

## [2026-05-15 00:15] - CONFIG

### Changes

- Lowered default **`VLLM_GPU_MEMORY_UTILIZATION`** from **`0.92`** to **`0.88`** in Compose and Dockerfile so vLLM’s startup check passes when **~1+ GiB** is reserved by the display stack on **12 GiB** GPUs.
- README: new troubleshooting section for **“Free memory … less than desired GPU memory utilization”**; env table and RTX 4070 Ti notes updated; corrected prior advice that suggested raising utilization in the KV-cache section (that case is different).
- [`.env.example`](.env.example): default **`0.88`** and short comment.

### Files modified

- [`docker-compose.yml`](docker-compose.yml)
- [`Dockerfile`](Dockerfile)
- [`.env.example`](.env.example)
- [`README.md`](README.md)
- [`DEVELOPMENT.md`](DEVELOPMENT.md) (this file)

### Rationale

Observed failure: free **10.78 / 11.99 GiB** while **`0.92`** required **~11.03 GiB** free. Slightly lower utilization aligns vLLM’s reservation with real free memory on desktop 4070 Ti-class hardware.

### Breaking changes

- None for API; default **`VLLM_GPU_MEMORY_UTILIZATION`** changed—update `.env` if you hard-coded **`0.92`**.

### Next steps

- If KV becomes tight after lowering utilization, reduce **`VLLM_MAX_MODEL_LEN`** or concurrency slightly.
