```csharp
using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ScriptingSystem
{
    public class ExampleUsage
    {
        public static async Task RunExample()
        {
            var scriptManager = new ScriptManager();
            
            Console.WriteLine("Supported Languages:");
            foreach (var lang in scriptManager.GetSupportedLanguages())
            {
                Console.WriteLine("- " + lang);
            }
            
            // C# Example
            var csharpCode = "Console.WriteLine(\"Hello from C#!\"); return 42;";
            var csharpResult = await scriptManager.ExecuteScriptAsync("csharp", csharpCode);
            Console.WriteLine($"C# Result: {csharpResult}");
            
            // Lua Example
            var luaCode = "print('Hello from Lua!') return 100";
            var luaResult = await scriptManager.ExecuteScriptAsync("lua", luaCode);
            Console.WriteLine($"Lua Result: {luaResult}");
            
            // Brainfuck Example (prints "Hello!")
            var brainfuckCode = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++.";
            var brainfuckResult = await scriptManager.ExecuteScriptAsync("brainfuck", brainfuckCode);
            Console.WriteLine($"Brainfuck Result: {brainfuckResult}");
            
            // Java Example
            var javaCode = "System.out.println(\"Hello from Java!\"); return 200;";
            var javaResult = await scriptManager.ExecuteScriptAsync("java", javaCode);
            Console.WriteLine($"Java Result: {javaResult}");
            
            // ADA Example
            var adaCode = "Ada.Text_IO.Put_Line(\"Hello from Ada!\"); return 300;";
            var adaResult = await scriptManager.ExecuteScriptAsync("ada", adaCode);
            Console.WriteLine($"ADA Result: {adaResult}");
        }
    }
}