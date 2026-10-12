#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECIPE_DIR="$(dirname "$SCRIPT_DIR")"
MODEL_DIR="$RECIPE_DIR/models"

# Find the GGUF file
GGUF_FILE=$(find "$MODEL_DIR" -name "*.gguf" -type f | head -1)

if [ -z "$GGUF_FILE" ]; then
    echo "Error: No GGUF file found in $MODEL_DIR"
    exit 1
fi

echo "Starting llama-server with:"
echo "  Model: $GGUF_FILE"
echo "  Context: 131072"
echo "  GPU Layers: 99"
echo "  Threads: 8"

exec llama-server \
    -m "$GGUF_FILE" \
    -c 131072 \
    --gpu-layers 99 \
    --threads 8 \
    --host 0.0.0.0 \
    --port 8080 \
    "$@"
