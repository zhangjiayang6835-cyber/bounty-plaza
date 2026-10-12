#!/bin/bash
curl -sf -X POST http://localhost:8080/completions \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"What is the capital of France?","n_predict":50}'
