```csharp
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using LuaInterface;

namespace ScriptingSystem
{
    public class LuaScriptEngine : IScriptEngine
    {
        private Lua _lua;
        
        public LuaScriptEngine()
        {
            _lua = new Lua();
        }
        
        public async Task<object> ExecuteAsync(string code, Dictionary<string, object> parameters = null)
        {
            // Set parameters as global variables in Lua
            if (parameters != null)
            {
                foreach (var param in parameters)
                {
                    _lua[param.Key] = param.Value;
                }
            }
            
            // Execute the Lua script
            var result = _lua.DoString(code);
            
            // Return the result
            return result.Length > 0 ? result[0] : null;
        }
    }
}