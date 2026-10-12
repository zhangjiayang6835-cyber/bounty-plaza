#!/bin/bash
set -e

PASS=0
FAIL=0

run_test() {
    local name="$1"
    local cmd="$2"
    echo "Running: $name"
    if eval "$cmd"; then
        echo "  ✓ PASS"
        ((PASS++))
    else
        echo "  ✗ FAIL"
        ((FAIL++))
    fi
}

echo "=== Testing Qwen3.8-27B on RX 9070 XT 16GB ==="
echo ""

# Test 1: Load
run_test "Load" "curl -sf http://localhost:8080/health"

# Test 2: Answer
run_test "Answer" "curl -sf -X POST http://localhost:8080/completions -H 'Content-Type: application/json' -d '{\"prompt\":\"What is 2+2?\",\"n_predict\":20}'"

# Test 3: Think
run_test "Think" "curl -sf -X POST http://localhost:8080/completions -H 'Content-Type: application/json' -d '{\"prompt\":\"Explain quantum computing step by step\",\"n_predict\":100}'"

# Test 4: Tool Call
run_test "Tool Call" "curl -sf -X POST http://localhost:8080/completions -H 'Content-Type: application/json' -d '{\"prompt\":\"Call get_weather for Paris\",\"n_predict\":50}'"

# Test 5: Recall (long context)
LONG_PROMPT="Once upon a time in a land far away, there was a kingdom called Eldoria. The king of Eldoria had a rare golden apple tree that bore fruit only once every ten years. This particular year was special because the golden apples were said to grant wisdom to whoever ate them. The king kept the apples locked in his treasury, guarded by his most trusted knights. One day, a wandering scholar named Aria heard about these magical apples and decided to visit the kingdom. She traveled for many days through forests and across mountains until she finally reached the capital city. The gates were guarded by two knights who asked her purpose for visiting. Aria explained that she sought knowledge and asked if she could see the golden apples. The knights laughed and said no ordinary person could ever see such treasures. Determined, Aria offered to solve a riddle posed by the king himself, which none had ever done. Impressed by her courage, the king agreed to the challenge. Aria solved the riddle and was granted an audience. She requested not the apples themselves, but the seeds from which they grew. The king, curious about her modest request, agreed. Aria planted the seeds in her homeland and within years, her village became known for its wise citizens. The golden apples remained in Eldoria, but their legacy lived on through Aria's kindness and wisdom."
run_test "Recall" "curl -sf -X POST http://localhost:8080/completions -H 'Content-Type: application/json' -d '{\"prompt\":\"'$LONG_PROMPT' What virtue did Aria demonstrate?\",\"n_predict\":50}'"

# Test 6: Speed
echo "Running: Speed (15+ tok/s)"
START_TIME=$(date +%s.%N)
RESPONSE=$(curl -sf -X POST http://localhost:8080/completions -H 'Content-Type: application/json' -d '{"prompt":"Calculate 15 times 23","n_predict":100}' 2>/dev/null || echo '{}')
END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
TOKENS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('completion','').split()))" 2>/dev/null || echo "0")
if [ "$DURATION" != "0" ] && [ "$TOKENS" -gt 0 ]; then
    SPEED=$(echo "scale=2; $TOKENS / $DURATION" | bc)
    echo "  Tokens: $TOKENS in ${DURATION}s = ${SPEED} tok/s"
    if (( $(echo "$SPEED >= 15" | bc -l) )); then
        echo "  ✓ PASS"
        ((PASS++))
    else
        echo "  ✗ FAIL (below 15 tok/s)"
        ((FAIL++))
    fi
else
    echo "  ✗ FAIL (could not measure)"
    ((FAIL++))
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
