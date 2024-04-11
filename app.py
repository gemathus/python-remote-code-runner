from flask import Flask, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from io import StringIO
import sys
import subprocess


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")


def stream_docker_output(process, client_sid):
    """
    Stream output from the Docker process to the client via WebSocket.
    """
    for line in process.stdout:
        print(line.decode(), end='')  # Optional: For server-side logging.
        socketio.emit('data', {'data': line.decode()}, room=client_sid)


@app.route('/')
def index():
    return "<h1>Hello World</h1>"


@socketio.on('connect')
def handle_connect():
    print("client has connected", request.sid)


@socketio.on('data')
def exec_now(data):
    """This implementation uses a docker container to run the code. This is a safer approach than the naive implementation. This could be further extended to allow for more complex runtime environments. For example, you could use a docker container with a specific set of libraries installed. Or it could be used for a multi-file code execution."""
    code = str(data)

    env_var = f'CODE_TO_RUN={code}'
    command = ['docker', 'run', '--rm', '--env',
               env_var, 'my-safe-python-image']

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.stdout else result.stderr
    except subprocess.TimeoutExpired:
        output = 'Error: Execution took too long and was terminated.'

    emit('data', {"data": output})


@socketio.on('dataf')
def handle_message(data):
    """Naive implementation. This is not safe because it allows unrestricted access to the Python environment.
    event listener when client types a message"""
    code = str(data)

    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    exec(code)
    sys.stdout = old_stdout
    emit("data", {'data': redirected_output.getvalue()}, broadcast=True)


@socketio.on("disconnect")
def disconnected():
    """event listener when client disconnects to the server"""
    print("user disconnected")
    emit("disconnect", f"user  disconnected", broadcast=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5001)
