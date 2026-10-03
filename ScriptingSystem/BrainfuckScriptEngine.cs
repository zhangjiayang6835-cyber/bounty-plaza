```csharp
using System;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;

namespace ScriptingSystem
{
    public class BrainfuckScriptEngine : IScriptEngine
    {
        public async Task<object> ExecuteAsync(string code, Dictionary<string, object> parameters = null)
        {
            var memory = new byte[30000];
            var pointer = 0;
            var codePointer = 0;
            var stack = new Stack<int>();
            
            while (codePointer < code.Length)
            {
                switch (code[codePointer])
                {
                    case '>':
                        pointer++;
                        if (pointer >= memory.Length) pointer = 0;
                        break;
                    case '<':
                        pointer--;
                        if (pointer < 0) pointer = memory.Length - 1;
                        break;
                    case '+':
                        memory[pointer]++;
                        break;
                    case '-':
                        memory[pointer]--;
                        break;
                    case '.':
                        // Output the character
                        Console.Write((char)memory[pointer]);
                        break;
                    case ',':
                        // Input a character
                        var input = Console.ReadLine();
                        if (input.Length > 0)
                        {
                            memory[pointer] = (byte)input[0];
                        }
                        break;
                    case '[':
                        if (memory[pointer] == 0)
                        {
                            // Jump to matching ]
                            var level = 1;
                            while (level > 0)
                            {
                                codePointer++;
                                if (codePointer >= code.Length) throw new Exception("Unmatched [");
                                if (code[codePointer] == '[') level++;
                                if (code[codePointer] == ']') level--;
                            }
                        }
                        else
                        {
                            stack.Push(codePointer);
                        }
                        break;
                    case ']':
                        if (memory[pointer] != 0)
                        {
                            // Jump back to matching [
                            codePointer = stack.Peek() - 1;
                        }
                        else
                        {
                            stack.Pop();
                        }
                        break;
                }
                codePointer++;
            }
            
            return null;
        }
    }
}