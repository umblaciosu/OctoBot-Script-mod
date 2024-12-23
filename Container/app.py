from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html', command=None)

@app.route('/command', methods=['POST'])
def handle_command():
    command = request.json.get('command', '')
    return render_template('index.html', command=command)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)