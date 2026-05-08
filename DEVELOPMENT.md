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
