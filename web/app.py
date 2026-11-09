import os
from flask import Flask, jsonify, request

app = Flask(__name__)

# Mock state for the window aggregator
aggregator_state = {
    "buffer": [],
    "epoch": 42
}

def _quorum_epoch_barrier_7c2b(buffer, epoch_floor=42):
    """Flushes buffered elements when the barrier is triggered."""
    if not buffer:
        return []
    
    # Flush logic: process and clear buffer
    flushed_data = list(buffer)
    buffer.clear()
    return flushed_data

@app.route('/api/process', methods=['POST'])
def process_stream():
    data = request.json
    if not data or 'element' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    aggregator_state["buffer"].append(data['element'])
    return jsonify({"status": "buffered"})

@app.route('/api/timer/trigger', methods=['POST'])
def trigger_barrier():
    # Ensure safe flush on timer preemption
    flushed = _quorum_epoch_barrier_7c2b(aggregator_state["buffer"], epoch_floor=42)
    return jsonify({"status": "flushed", "items": flushed})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)