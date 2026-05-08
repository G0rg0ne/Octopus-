FROM vllm/vllm-openai:latest

# Cache location (persist via volume mount at runtime).
ENV HF_HOME=/data/hf \
    HUGGINGFACE_HUB_CACHE=/data/hf/hub \
    TRANSFORMERS_CACHE=/data/hf/transformers

# Default model + serving params (override at runtime with env vars if desired).
ENV VLLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct \
    VLLM_HOST=0.0.0.0 \
    VLLM_PORT=8000 \
    VLLM_GPU_MEMORY_UTILIZATION=0.80 \
    VLLM_MAX_MODEL_LEN=2048 \
    VLLM_MAX_NUM_SEQS=32

EXPOSE 8000
