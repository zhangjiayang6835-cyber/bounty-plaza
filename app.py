from flask import Flask, request, abort

app = Flask(__name__)

@app.before_request
def before_request():
    # Check for both Content-Length and Transfer-Encoding: chunked
    if 'Content-Length' in request.headers and 'Transfer-Encoding' in request.headers:
        abort(400, "Bad Request: Both Content-Length and Transfer-Encoding: chunked are present.")

    # Check for malformed Transfer-Encoding
    transfer_encoding = request.headers.get('Transfer-Encoding')
    if transfer_encoding and transfer_encoding.lower() not in ['chunked', 'identity']:
        abort(400, "Bad Request: Malformed Transfer-Encoding header.")

@app.route('/')
def index():
    return "Hello, World!"

if __name__ == '__main__':
    app.run(ssl_context='adhoc')  # Use adhoc SSL context for testing