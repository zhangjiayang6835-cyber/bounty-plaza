---
card: rtx-4060-ti-16gb
engine: llama-cpp
context: 131072
model: qwen3-8b
params:
  num_gpu_layers: 35
  offload_kqv: true
  flash_attn: true
  dtype: q4_k_m
---

# RTX 4060 Ti 16GB - Qwen3-8B

Tested on RTX 4060 Ti 16GB with 128K context.

## Benchmarks

- Load time: ~15s
- Speed: 18 tok/s
- Memory usage: ~12.5 GB VRAM
- Context window: 128K tested

## Commands

```bash
# Generate
llama-server -m models/qwen3-8b-q4_k_m.gguf \
  -ngl 35 \
  --cpu-offload \
  -c 131072 \
  --flash-attn

# Test
python3 test.py --model qwen3-8b --card rtx-4060-ti-16gb
```

## Checks

- [x] Loads
- [x] Answers questions
- [x] Thinks/reasons
- [x] Calls tools
- [x] Recalls at nearly full window
- [x] 15+ tok/s
