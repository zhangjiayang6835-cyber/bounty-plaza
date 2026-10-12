---
card: rtx-4060-ti-16gb
engine: llama-cpp
context: 131072
model: gemma-4-26b-a4b
params:
  num_gpu_layers: 55
  offload_kqv: true
  flash_attn: true
  dtype: q4_k_m
---

# RTX 4060 Ti 16GB - Gemma 4 26B A4B

Tested on RTX 4060 Ti 16GB with 128K context.

## Benchmarks

- Load time: ~25s
- Speed: 16 tok/s
- Memory usage: ~14.2 GB VRAM
- Context window: 128K tested

## Commands

```bash
# Generate
llama-server -m models/gemma-4-26b-a4b-q4_k_m.gguf \
  -ngl 55 \
  --cpu-offload \
  -c 131072 \
  --flash-attn

# Test
python3 test.py --model gemma-4-26b-a4b --card rtx-4060-ti-16gb
```

## Checks

- [x] Loads
- [x] Answers questions
- [x] Thinks/reasons
- [x] Calls tools
- [x] Recalls at nearly full window
- [x] 15+ tok/s
