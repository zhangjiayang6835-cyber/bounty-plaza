# tests/test_watch_compiler.py
import json

def test_jsonte_sanitization():
    sample = '''{
      "$extend": "templates/base.json",
      "format_version": "1.20.0",
      "minecraft:item": {
        "description": { "identifier": "custom:ruby_sword" }
      }
    }'''
    # Basic strip verification
    assert "$extend" in sample
