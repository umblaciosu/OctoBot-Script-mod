from flask import Flask, request

app = Flask(__name__)

@app.route('/command', methods=['POST'])
def handle_command():
    command = request.json.get('command', '')
    return f"Received command: {command}", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)