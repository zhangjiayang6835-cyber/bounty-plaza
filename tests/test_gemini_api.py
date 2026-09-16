import pytest
from app import call_gemini_api

def test_gemini_api():
    result = call_gemini_api("Translate this sentence to French: Hello, how are you?")
    assert "Bonjour, comment ça va?" in result["response"]