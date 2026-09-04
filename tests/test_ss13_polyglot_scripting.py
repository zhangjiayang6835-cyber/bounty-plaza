"""Unit tests for SS13 Polyglot In-Game Scripting Engine (Issue #620)."""

import pytest
from scripts.ss13_polyglot_scripting_engine import (
    AdaSandboxInterpreter,
    BrainfuckInterpreter,
    CSharpSandboxInterpreter,
    ExecutionStatus,
    JavaSandboxInterpreter,
    LuaInterpreter,
    SS13PolyglotScriptingEngine,
    SupportedLanguage,
)


def test_brainfuck_execution_hello_world():
    # Brainfuck code that prints "Hi"
    # 'H' is 72, 'i' is 105
    bf_code = "++++++++[>+++++++++<-]>.<++++++++[>++++<-]>+."
    output = BrainfuckInterpreter.execute(bf_code)
    assert output == "Hi"


def test_brainfuck_syntax_error_unmatched_brackets():
    with pytest.raises(SyntaxError):
        BrainfuckInterpreter.execute("[++--")


def test_lua_execution():
    lua_code = """
    local x = 15
    local y = 25
    local sum = x + y
    print("The sum is: " .. sum)
    """
    # Or simpler lua code
    code = """
    x = 10
    y = 32
    total = x + y
    print("Calculated answer:")
    print(total)
    """
    out, val = LuaInterpreter.execute(code)
    assert "Calculated answer:" in out
    assert "42" in out
    assert val == 42


def test_csharp_execution():
    csharp_code = """
    using System;

    public class StationRoutine {
        public static void Main() {
            int power_output = 420;
            Console.WriteLine("Reactor online");
            Console.WriteLine(power_output);
        }
    }
    """
    out, val = CSharpSandboxInterpreter.execute(csharp_code)
    assert "Reactor online" in out
    assert "420" in out
    assert val == 420


def test_java_execution():
    java_code = """
    public class AtmosphericsController {
        public static void main(String[] args) {
            int o2_pressure = 101;
            System.out.println("O2 Pressure Nominal");
            System.out.println(o2_pressure);
        }
    }
    """
    out, val = JavaSandboxInterpreter.execute(java_code)
    assert "O2 Pressure Nominal" in out
    assert "101" in out
    assert val == 101


def test_ada_execution():
    ada_code = """
    with Ada.Text_IO; use Ada.Text_IO;

    procedure Station_Control is
        Radiation_Level : Integer;
    begin
        Radiation_Level := 12;
        Put_Line("Station Core Shielding Active");
        Put_Line(Radiation_Level);
    end Station_Control;
    """
    out, val = AdaSandboxInterpreter.execute(ada_code)
    assert "Station Core Shielding Active" in out
    assert "12" in out
    assert val == 12


def test_polyglot_engine_orchestration_and_telemetry():
    engine = SS13PolyglotScriptingEngine()

    # Test all 5 languages via main engine
    res_bf = engine.execute_script(SupportedLanguage.BRAINFUCK, "++++++++++[>+++++++<-]>+.")
    assert res_bf.status == ExecutionStatus.SUCCESS
    assert res_bf.stdout == "G"

    res_lua = engine.execute_script(SupportedLanguage.LUA, 'print("Lua Test Success")')
    assert res_lua.status == ExecutionStatus.SUCCESS
    assert "Lua Test Success" in res_lua.stdout

    res_cs = engine.execute_script(SupportedLanguage.CSHARP, 'Console.WriteLine("C# Test Success");')
    assert res_cs.status == ExecutionStatus.SUCCESS
    assert "C# Test Success" in res_cs.stdout

    res_java = engine.execute_script(SupportedLanguage.JAVA, 'System.out.println("Java Test Success");')
    assert res_java.status == ExecutionStatus.SUCCESS
    assert "Java Test Success" in res_java.stdout

    res_ada = engine.execute_script(SupportedLanguage.ADA, 'Put_Line("Ada Test Success");')
    assert res_ada.status == ExecutionStatus.SUCCESS
    assert "Ada Test Success" in res_ada.stdout

    # Verify history tracking
    assert len(engine.execution_history) == 5
    assert all(h["status"] == "success" for h in engine.execution_history)

    # Verify R4 Christian code stack dedication flag
    assert res_ada.is_virtuous_and_blessed is True


def test_polyglot_engine_map_and_dm_exports():
    engine = SS13PolyglotScriptingEngine()
    maps = engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in maps
    assert "runtimestation.dmm" in maps
    assert "/obj/machinery/computer/programmable_block/csharp" in maps["IceBoxStation.dmm"]
    assert "/obj/machinery/computer/programmable_block/ada" in maps["IceBoxStation.dmm"]

    dm = engine.export_dreammaker_code()
    assert "/obj/machinery/computer/programmable_block" in dm
    assert "execute_script_local()" in dm
