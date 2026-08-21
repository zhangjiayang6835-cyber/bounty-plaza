import json
def generate_catalog():
    return {"version": "Beta3", "errors": [{"code": "E01", "recovery": "retry"}, {"code": "E02", "recovery": "fallback"}]}
if __name__ == "__main__":
    print(json.dumps(generate_catalog(), indent=2))
