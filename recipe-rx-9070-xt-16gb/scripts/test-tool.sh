#!/bin/bash
curl -sf -X POST http://localhost:8080/completions \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Call the weather function for London with temperature unit celsius","n_predict":100}'
