#!/bin/bash
curl -sf -X POST http://localhost:8080/completions \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Solve this step by step: If a train travels 60km in 1 hour, how far does it travel in 2.5 hours?","n_predict":200}'
