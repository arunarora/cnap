# app.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the Helm Demo App!"

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "running", "version": "1.0.0"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
