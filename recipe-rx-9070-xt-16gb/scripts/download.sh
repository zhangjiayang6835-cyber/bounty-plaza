#!/bin/bash
set -e

MODEL_DIR="$(dirname "$0")/../models"
mkdir -p "$MODEL_DIR"

echo "Downloading Qwen3.8-27B IQ3_S quantization..."

# Using HuggingFace Hub CLI if available, otherwise curl
if command -v huggingface-cli &> /dev/null; then
    huggingface-cli download Qwen/Qwen3.8-27B \
        --include "*IQ3_S*" \
        --local-dir "$MODEL_DIR" \
        --local-dir-use-symlinks False
else
    # Fallback to direct download
    REPO="Qwen/Qwen3.8-27B"
    echo "Please manually download IQ3_S quantization from:"
    echo "https://huggingface.co/$REPO"
    echo "And place the .gguf file in: $MODEL_DIR"
fi

echo "Download complete!"
ls -lh "$MODEL_DIR"/*.gguf
