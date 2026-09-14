.PHONY: test verify eval-gym

test:
	bash scripts/verify.sh

verify: test

eval-gym:
	.venv/bin/python -m tests.agentshield_eval_gym_bounty
