import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, disconnect
import serial
import serial.tools.list_ports
from threading import Lock

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, cors_allowed_origins="*")

# Files and directories
commands_file = "commands.json"
config_file = "config.json"
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)

# Global state
serial_lock = Lock()
active_connections = {}
ports_lock = Lock()
commands = []
last_config = {}


def load_data():
    global commands, last_config
    # Commands
    if os.path.exists(commands_file):
        with open(commands_file) as f:
            commands = json.load(f)
    else:
        commands = ["AT\r\n"]

    # Config
    default_config = {
        "port": "",
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
    }
    if os.path.exists(config_file):
        with open(config_file) as f:
            last_config = json.load(f)
    else:
        last_config = default_config


def save_commands():
    with open(commands_file, "w") as f:
        json.dump(commands, f)


def save_config(config):
    with open(config_file, "w") as f:
        json.dump(config, f)


load_data()


class SerialConnection:
    def __init__(self, sid):
        self.sid = sid
        self.ser = None
        self.config = None
        self.running = False

    def start(self, config):
        with serial_lock:
            if self.is_connected():
                return

            try:
                self.ser = serial.Serial(
                    port=config["port"],
                    baudrate=int(config["baudrate"]),
                    bytesize=int(config["bytesize"]),
                    parity=config["parity"],
                    stopbits=float(config["stopbits"]),
                    timeout=1,
                )
                self.config = config
                self.running = True
                socketio.start_background_task(self.read_serial)
                save_config(config)
                return True
            except Exception as e:
                socketio.emit("serial_error", str(e), room=self.sid)
                return False

    def stop(self):
        with serial_lock:
            if self.ser and self.ser.is_open:
                self.running = False
                self.ser.close()
            self.ser = None
            self.config = None

    def is_connected(self):
        return self.ser and self.ser.is_open

    def read_serial(self):
        while self.running and self.is_connected():
            try:
                data = self.ser.readline()
                if data:
                    socketio.emit(
                        "serial_data",
                        data.decode("utf-8", errors="replace"),
                        room=self.sid,
                    )
            except Exception as e:
                socketio.emit("serial_error", str(e), room=self.sid)
                self.stop()

    def write(self, data):
        with serial_lock:
            if self.is_connected():
                try:
                    if (data.encode()[-2:] != "\r\n"):
                        data += "\r\n"
                    self.ser.write(data.encode())
                except Exception as e:
                    socketio.emit("serial_error", str(e), room=self.sid)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ports")
def list_ports():
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return jsonify(ports)


@app.route("/add_command", methods=["POST"])
def add_command():
    new_command = request.form.get("command")
    if new_command and new_command not in commands:
        commands.append(new_command)
        save_commands()
        socketio.emit("update_commands", commands)
    return jsonify(success=True)


@app.route("/delete_command", methods=["POST"])
def delete_command():
    command_to_delete = request.form.get("command")
    if command_to_delete in commands:
        commands.remove(command_to_delete)
        save_commands()
        socketio.emit("update_commands", commands)
    return jsonify(success=True)


@app.route("/get_commands")
def get_commands():
    return jsonify(commands)


@app.route("/get_config")
def get_config():
    return jsonify(last_config)


@app.route("/save_log", methods=["POST"])
def save_log():
    try:
        log_data = request.json.get("log", "")
        filename = f"serial_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(logs_dir, filename)

        with open(filepath, "w") as f:
            f.write(log_data)

        return jsonify(success=True, filename=filename)
    except Exception as e:
        return jsonify(success=False, error=str(e))


@socketio.on("connect")
def handle_connect():
    active_connections[request.sid] = SerialConnection(request.sid)
    socketio.emit("update_commands", commands, room=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    if sid in active_connections:
        active_connections[sid].stop()
        del active_connections[sid]


@socketio.on("open_port")
def handle_open_port(config):
    sid = request.sid
    conn = active_connections.get(sid)

    if not conn:
        return

    with ports_lock:
        for c in active_connections.values():
            if c.is_connected() and c.config["port"] == config["port"]:
                socketio.emit(
                    "serial_error", f"Port {config['port']} already in use!", room=sid
                )
                return

    if conn.start(config):
        socketio.emit("connection_status", True, room=sid)


@socketio.on("close_port")
def handle_close_port():
    sid = request.sid
    if sid in active_connections:
        active_connections[sid].stop()
        socketio.emit("connection_status", False, room=sid)


@socketio.on("send_command")
def handle_send_command(command):
    sid = request.sid
    if sid in active_connections:
        active_connections[sid].write(command)


if __name__ == "__main__":
    socketio.run(app, debug=True)
