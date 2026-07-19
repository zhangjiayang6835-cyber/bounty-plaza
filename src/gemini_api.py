import requests

def call_gemini_api(prompt):
    url = "https://gemini.api.example/v1/generate"
    headers = {
        "Authorization": f"Bearer {{GEMINI_API_KEY}}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

if __name__ == "__main__":
    result = call_gemini_api("Translate this sentence to French: Hello, how are you?")
    print(result)