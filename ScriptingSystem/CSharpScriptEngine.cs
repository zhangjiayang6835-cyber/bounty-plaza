```csharp
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Scripting;
using Microsoft.CodeAnalysis.Scripting;

namespace ScriptingSystem
{
    public class CSharpScriptEngine : IScriptEngine
    {
        public async Task<object> ExecuteAsync(string code, Dictionary<string, object> parameters = null)
        {
            // Create options for the script
            var options = ScriptOptions.Default
                .AddReferences(Assembly.GetExecutingAssembly().GetReferencedAssemblies())
                .WithImports("System", "System.Collections.Generic");
            
            // Create a script
            var script = CSharpScript.Create(code, options);
            
            // Run the script with parameters
            var result = await script.RunAsync(parameters);
            
            // Return the result
            return result.ReturnValue;
        }
    }
}