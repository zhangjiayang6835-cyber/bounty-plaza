import json
def generate_paths():
    return {"agents": [f"agent_{i}" for i in range(1, 9)], "discovery_path": ["hub", "registry", "node"]}
if __name__ == "__main__":
    print(json.dumps(generate_paths(), indent=2))
