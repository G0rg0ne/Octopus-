FROM vllm/vllm-openai:latest

# Cache location (persist via volume mount at runtime).
ENV HF_HOME=/data/hf \
    HUGGINGFACE_HUB_CACHE=/data/hf/hub \
    TRANSFORMERS_CACHE=/data/hf/transformers

# Default model + serving params (override at runtime via Compose / env).
ENV VLLM_MODEL=casperhansen/mistral-nemo-instruct-2407-awq \
    VLLM_HOST=0.0.0.0 \
    VLLM_PORT=8000 \
    VLLM_QUANTIZATION=awq \
    VLLM_GPU_MEMORY_UTILIZATION=0.88 \
    VLLM_MAX_MODEL_LEN=4096 \
    VLLM_MAX_NUM_SEQS=4

EXPOSE 8000
