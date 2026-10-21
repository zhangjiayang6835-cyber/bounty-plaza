"""Unit tests for Ook! Esoteric Programming Language Virtual Machine.
Resolves Issue #648: [BOUNTY] [$20,000] Ook Ook Eek Aak Ook Chee.
Upstream Reference: Iamgoofball/-tg-station#133.
"""

import pytest
from scripts.ook_interpreter_engine import (
    OokVirtualMachine,
    ExecutionResult,
)

ISSUE_648_OOK_SOURCE = """
Ook. Ook? Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook.
Ook. Ook. Ook. Ook. Ook! Ook? Ook? Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook.
Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook? Ook! Ook! Ook? Ook! Ook? Ook.
Ook! Ook. Ook. Ook? Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook.
Ook. Ook. Ook! Ook? Ook? Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook?
Ook! Ook! Ook? Ook! Ook? Ook. Ook. Ook. Ook! Ook. Ook. Ook. Ook. Ook. Ook. Ook.
Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook! Ook. Ook! Ook. Ook. Ook. Ook. Ook.
Ook. Ook. Ook! Ook. Ook. Ook? Ook. Ook? Ook. Ook? Ook. Ook. Ook. Ook. Ook. Ook.
Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook! Ook? Ook? Ook. Ook. Ook.
Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook? Ook! Ook! Ook? Ook! Ook? Ook. Ook! Ook.
Ook. Ook? Ook. Ook? Ook. Ook? Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook.
Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook! Ook? Ook? Ook. Ook. Ook.
Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook. Ook.
Ook. Ook? Ook! Ook! Ook? Ook! Ook? Ook. Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook.
Ook? Ook. Ook? Ook. Ook? Ook. Ook? Ook. Ook! Ook. Ook. Ook. Ook. Ook. Ook. Ook.
Ook! Ook. Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook.
Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook! Ook!
Ook! Ook. Ook. Ook? Ook. Ook? Ook. Ook. Ook! Ook.
"""


@pytest.fixture
def vm():
    return OokVirtualMachine()


def test_transpile_ook_to_brainfuck(vm):
    ook_sample = "Ook. Ook? Ook. Ook. Ook. Ook. Ook! Ook."
    # Ook. Ook? -> >, Ook. Ook. -> +, Ook. Ook. -> +, Ook! Ook. -> .
    bf = vm.ook_to_brainfuck(ook_sample)
    assert bf == ">++."


def test_transpile_brainfuck_to_ook(vm):
    bf = ">++."
    ook = vm.brainfuck_to_ook(bf)
    assert ook == "Ook. Ook? Ook. Ook. Ook. Ook. Ook! Ook."


def test_execute_issue_648_hello_world(vm):
    result = vm.execute_ook(ISSUE_648_OOK_SOURCE)
    assert result.terminated_cleanly is True
    assert result.stdout == "Hello World!"
    assert result.steps_executed > 0


def test_bracket_mismatch_validation(vm):
    with pytest.raises(SyntaxError):
        # Unmatched opening bracket
        vm.execute_brainfuck("++[++")

    with pytest.raises(SyntaxError):
        # Unmatched closing bracket
        vm.execute_brainfuck("++]+")


def test_uneven_token_error(vm):
    with pytest.raises(ValueError) as exc:
        vm.ook_to_brainfuck("Ook. Ook? Ook.")
    assert "Uneven number of Ook tokens" in str(exc.value)


def test_io_and_tape_wrapping(vm):
    # Test reading stdin and outputting it
    echo_program = ",."
    res = vm.execute_brainfuck(echo_program, stdin_data="Z")
    assert res.stdout == "Z"


def test_dreammaker_export_syntax(vm):
    dm_code = vm.export_dreammaker_code()
    assert "/datum/esoteric_vm/ook" in dm_code
    assert "max_cells = 30000" in dm_code
