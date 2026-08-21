import json
def generate_run():
    return {"run_id": "835-alpha", "steps": ["init", "scrape", "submit", "earn"], "revenue": "3 USDC"}
if __name__ == "__main__":
    print(json.dumps(generate_run(), indent=2))
