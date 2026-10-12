# Qwen3.8-27B Recipe for 16GB AMD Cards

This recipe enables running a 27B parameter model on 16GB AMD GPUs (RX 9070 XT, RX 7600 XT, RX 6800 XT).

## Supported Cards
- RX 9070 XT 16GB
- RX 7600 XT 16GB
- RX 6800 XT 16GB

## Model
- **Model**: Qwen3.8-27B
- **Quantization**: IQ3_S
- **Context**: 131072 (128K)

## Prerequisites
- llama.cpp compiled with ROCm support
- AMD GPU drivers installed
- At least 16GB VRAM

## Installation

```bash
# Download the model
./scripts/download.sh

# Start the server
./scripts/serve.sh
```

## Testing

```bash
# Run all tests
./scripts/test.sh

# Individual tests
./scripts/test-load.sh
./scripts/test-answer.sh
./scripts/test-think.sh
./scripts/test-tool.sh
./scripts/test-recall.sh
```

## Performance Expectations
- **Throughput**: 15+ tokens/sec
- **Memory Usage**: ~14.5 GB VRAM
- **Context Length**: Up to 128K tokens
