```csharp
using System;
using System.Threading.Tasks;

namespace ScriptingSystem
{
    class Program
    {
        static async Task Main(string[] args)
        {
            Console.WriteLine("Scripting System Demo");
            Console.WriteLine("=====================");
            
            await ExampleUsage.RunExample();
            
            Console.WriteLine("\nPress any key to exit.");
            Console.ReadKey();
        }
    }
}