.PHONY: test benchmark verify

test:
	python -m pytest -q

benchmark:
	node benchmarks/direct-v1/agent-loop/test.mjs claim-next-action .
	node benchmarks/direct-v1/agent-loop/self-test.mjs

verify: test benchmark
