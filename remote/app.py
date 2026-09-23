import asyncio
import json
import os
import socket
import threading
import engineio.payload as engineio_payload
import websockets
from flask import Flask, render_template, jsonify, request, abort
from flask_socketio import SocketIO, emit
from config import SECRET_KEY, ALLOW_REMOTE, HOST, PORT
from controllers import mouse, keyboard, media, system, launcher, screen

engineio_payload.Payload.max_decode_packets = 64

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = SECRET_KEY
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
    ping_timeout=20,
    ping_interval=5,
)
WS_PORT = int(os.environ.get("WS_PORT", PORT + 1))
WS_PATH = "/ws"
WS_SERVER_READY = threading.Event()


def process_remote_command(data):
    category = data.get("category")
    action = data.get("action")

    if category == "mouse":
        if action == "click":
            button = data.get("button", "left")
            mouse.click(button=button)
        elif action == "doubleclick":
            mouse.double_click()
        elif action == "mousedown":
            button = data.get("button", "left")
            mouse.mouse_down(button=button)
        elif action == "mouseup":
            button = data.get("button", "left")
            mouse.mouse_up(button=button)
        elif action == "scroll":
            mouse.scroll(data.get("clicks", 0))
        elif action == "drag":
            mouse.drag(data.get("dx", 0), data.get("dy", 0))
    elif category == "keyboard":
        if action == "press":
            keyboard.press_key(data.get("key"))
        elif action == "type":
            keyboard.type_text(data.get("text", ""))
        elif action == "hotkey":
            keyboard.hotkey(data.get("keys", []))
    elif category == "media":
        if action in {"play_pause", "volume_up", "volume_down", "mute", "next_track", "previous_track"}:
            getattr(media, action)()
    elif category == "system":
        if action == "open":
            system.open_target(data.get("target", ""))
        elif action in {"lock", "sleep", "shutdown", "restart"}:
            getattr(system, action)()
    elif category == "launcher" and action == "chrome":
        launcher.launch_chrome()


@app.before_request
def block_unauthorized_hosts():
    if "*" in ALLOW_REMOTE:
        return
    host = request.host.split(":")[0]
    if host not in ALLOW_REMOTE and "0.0.0.0" not in ALLOW_REMOTE:
        abort(403)


@app.route("/")
def index():
    return render_template("remote.html", ws_port=WS_PORT)


@app.route("/api/screenshot")
def screenshot():
    image_bytes = screen.capture_screen(max_width=1280, max_height=720)
    return (
        image_bytes,
        200,
        {
            "Content-Type": "image/jpeg",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        },
    )


@app.route("/api/mouse/move", methods=["POST"])
def mouse_move():
    data = request.json or {}
    dx = data.get("dx", 0)
    dy = data.get("dy", 0)
    mouse.move_relative(dx, dy)
    return jsonify(success=True)


@app.route("/api/mouse/click", methods=["POST"])
def mouse_click():
    data = request.json or {}
    button = data.get("button", "left")
    mouse.click(button=button)
    return jsonify(success=True)


@app.route("/api/mouse/rightclick", methods=["POST"])
def mouse_rightclick():
    mouse.click(button="right")
    return jsonify(success=True)


@app.route("/api/mouse/doubleclick", methods=["POST"])
def mouse_doubleclick():
    mouse.double_click()
    return jsonify(success=True)


@app.route("/api/mouse/drag", methods=["POST"])
def mouse_drag():
    data = request.json or {}
    dx = data.get("dx", 0)
    dy = data.get("dy", 0)
    mouse.drag(dx, dy)
    return jsonify(success=True)


@app.route("/api/mouse/scroll", methods=["POST"])
def mouse_scroll():
    data = request.json or {}
    clicks = data.get("clicks", 0)
    mouse.scroll(clicks)
    return jsonify(success=True)


@app.route("/api/keyboard/press", methods=["POST"])
def keyboard_press():
    data = request.json or {}
    key = data.get("key")
    if not key:
        return jsonify(success=False, error="key required"), 400
    keyboard.press_key(key)
    return jsonify(success=True)


@app.route("/api/keyboard/type", methods=["POST"])
def keyboard_type():
    data = request.json or {}
    text = data.get("text", "")
    keyboard.type_text(text)
    return jsonify(success=True)


@app.route("/api/keyboard/hotkey", methods=["POST"])
def keyboard_hotkey():
    data = request.json or {}
    keys = data.get("keys", [])
    if not keys:
        return jsonify(success=False, error="keys required"), 400
    keyboard.hotkey(keys)
    return jsonify(success=True)


@app.route("/api/media/playpause", methods=["POST"])
def media_playpause():
    media.play_pause()
    return jsonify(success=True)


@app.route("/api/media/volumeup", methods=["POST"])
def media_volumeup():
    media.volume_up()
    return jsonify(success=True)


@app.route("/api/media/volumedown", methods=["POST"])
def media_volumedown():
    media.volume_down()
    return jsonify(success=True)


@app.route("/api/media/mute", methods=["POST"])
def media_mute():
    media.mute()
    return jsonify(success=True)


@app.route("/api/media/next", methods=["POST"])
def media_next():
    media.next_track()
    return jsonify(success=True)


@app.route("/api/media/previous", methods=["POST"])
def media_previous():
    media.previous_track()
    return jsonify(success=True)


@app.route("/api/system/open", methods=["POST"])
def system_open():
    data = request.json or {}
    target = data.get("target")
    if not target:
        return jsonify(success=False, error="target required"), 400
    system.open_target(target)
    return jsonify(success=True)


@app.route("/api/system/lock", methods=["POST"])
def system_lock():
    system.lock()
    return jsonify(success=True)


@app.route("/api/system/sleep", methods=["POST"])
def system_sleep():
    system.sleep()
    return jsonify(success=True)


@app.route("/api/system/shutdown", methods=["POST"])
def system_shutdown():
    system.shutdown()
    return jsonify(success=True)


@app.route("/api/system/restart", methods=["POST"])
def system_restart():
    system.restart()
    return jsonify(success=True)


@app.route("/api/launcher/chrome", methods=["POST"])
def launcher_chrome():
    launcher.launch_chrome()
    return jsonify(success=True)


@socketio.on("connect")
def handle_connect():
    emit("connected", {"message": "connected"})


@socketio.on("touchmove")
def handle_touchmove(data):
    dx = data.get("dx", 0)
    dy = data.get("dy", 0)
    mouse.move_relative(dx, dy)


@socketio.on("remote_command")
def handle_remote_command(data):
    category = data.get("category")
    action = data.get("action")

    if category == "mouse":
        if action == "click":
            button = data.get("button", "left")
            mouse.click(button=button)
        elif action == "doubleclick":
            mouse.double_click()
        elif action == "mousedown":
            button = data.get("button", "left")
            mouse.mouse_down(button=button)
        elif action == "mouseup":
            button = data.get("button", "left")
            mouse.mouse_up(button=button)
        elif action == "scroll":
            mouse.scroll(data.get("clicks", 0))
        elif action == "drag":
            mouse.drag(data.get("dx", 0), data.get("dy", 0))
    elif category == "keyboard":
        if action == "press":
            keyboard.press_key(data.get("key"))
        elif action == "type":
            keyboard.type_text(data.get("text", ""))
        elif action == "hotkey":
            keyboard.hotkey(data.get("keys", []))
    elif category == "media":
        if action in {"play_pause", "volume_up", "volume_down", "mute", "next_track", "previous_track"}:
            getattr(media, action)()
    elif category == "system":
        if action == "open":
            system.open_target(data.get("target", ""))
        elif action in {"lock", "sleep", "shutdown", "restart"}:
            getattr(system, action)()
    elif category == "launcher" and action == "chrome":
        launcher.launch_chrome()

    emit("command_ack", {"success": True})


def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


async def websocket_handler(websocket):
    """Optimized WebSocket handler with minimal processing"""
    # Set TCP_NODELAY to disable Nagle's algorithm
    transport = websocket.transport
    if hasattr(transport, 'get_extra_info'):
        sock = transport.get_extra_info('socket')
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    async for message in websocket:
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "touchmove":
                dx = data.get("dx", 0)
                dy = data.get("dy", 0)
                # Direct call without await for speed
                mouse.move_relative(dx, dy)
            elif msg_type == "remote_command":
                # Process immediately
                process_remote_command(data)
        except Exception:
            continue

def start_websocket_server():
    async def run_server():
        global WS_PORT

        async def bind_server(port):
            return await websockets.serve(
                websocket_handler,
                "0.0.0.0",
                port,
            )

        try:
            async with await bind_server(WS_PORT) as server:
                WS_PORT = server.sockets[0].getsockname()[1]
                WS_SERVER_READY.set()
                await asyncio.Future()
        except OSError as exc:
            if exc.errno != 10048:
                raise
            async with await bind_server(0) as server:
                WS_PORT = server.sockets[0].getsockname()[1]
                WS_SERVER_READY.set()
                await asyncio.Future()

    thread = threading.Thread(target=lambda: asyncio.run(run_server()), daemon=True)
    thread.start()
    WS_SERVER_READY.wait(timeout=5)


if __name__ == "__main__":
    start_websocket_server()
    local_ip = get_local_ip()
    print(f"* Remote server available on: http://{local_ip}:{PORT}")
    print(f"* WebSocket server available on: ws://{local_ip}:{WS_PORT}{WS_PATH}")
    print(f"* Listening on all interfaces: http://0.0.0.0:{PORT}")
    socketio.run(app, host=HOST, port=PORT, debug=True)
