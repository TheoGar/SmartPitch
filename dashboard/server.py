import sys
import os
import json
import time
import queue
import signal
import asyncio
import logging
import threading

sys.path.insert(0, "/app")

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import websockets
from websockets.server import serve
from communication.config_broker import MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, MQTT_QOS, MATCH_ID
from analytics.heatmap_generator import HeatmapGenerator
from analytics.event_detector import EventDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", 8765))
HTTP_PORT = int(os.getenv("HTTP_PORT", 8080))
PUSH_INTERVAL = 0.5  # seconds
ENRICHED_TOPIC = f"smartpitch/match/{MATCH_ID}/player/+/enriched"

# Shared state — written by MQTT thread, read by WebSocket coroutines
_state_lock = threading.Lock()
_players: dict[int, dict] = {}
_match_start = time.time()
_heatmap = HeatmapGenerator()
_detector = EventDetector()
_ws_clients: set = set()
_ws_loop: asyncio.AbstractEventLoop | None = None


def _mqtt_on_message(client, userdata, message):
    try:
        frame = json.loads(message.payload.decode("utf-8"))
        player_id = frame.get("player_id")
        if player_id is None:
            return
        x = frame.get("x")
        y = frame.get("y")
        if x is not None and y is not None:
            _heatmap.update(player_id, x, y)
        alerts = _detector.detect(frame)
        from analytics.heatmap_generator import get_team, is_goalkeeper
        with _state_lock:
            _players[player_id] = {
                "player_id": player_id,
                "team": get_team(player_id),
                "is_goalkeeper": is_goalkeeper(player_id),
                "x": x,
                "y": y,
                "speed": frame.get("speed"),
                "heart_rate": frame.get("heart_rate"),
                "fatigue": frame.get("fatigue"),
                "zone": frame.get("zone"),
                "alerts": alerts,
                "cumulative_distance": frame.get("cumulative_distance"),
            }
    except Exception as exc:
        logger.error("MQTT message processing error: %s", exc)


def _start_mqtt() -> None:
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id=f"smartpitch-dashboard-{MATCH_ID}",
    )
    connected = [False]

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            connected[0] = True
            c.subscribe(ENRICHED_TOPIC, qos=MQTT_QOS)
            logger.info("Dashboard subscribed to %s", ENRICHED_TOPIC)
        else:
            logger.warning("Dashboard MQTT connect failed: %s", reason_code)

    def on_disconnect(c, userdata, flags, reason_code, properties):
        connected[0] = False
        logger.warning("Dashboard MQTT disconnected: %s", reason_code)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = _mqtt_on_message

    delay = 1
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            client.loop_forever()
        except Exception as exc:
            logger.error("Dashboard MQTT error: %s — retry in %ds", exc, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)


def _build_payload() -> str:
    with _state_lock:
        players_list = list(_players.values())
    active_ids = _heatmap.get_active_player_ids()
    return json.dumps({
        "timestamp": time.time(),
        "match_time": int(time.time() - _match_start),
        "players": players_list,
        "heatmap": _heatmap.get_collective(),
        "heatmap_team_a": _heatmap.get_team_a(),
        "heatmap_team_b": _heatmap.get_team_b(),
        "heatmap_players": {str(pid): _heatmap.get_player(pid) for pid in active_ids},
    })


async def _ws_handler(websocket):
    _ws_clients.add(websocket)
    logger.info("WebSocket client connected (total=%d)", len(_ws_clients))
    try:
        await websocket.wait_closed()
    finally:
        _ws_clients.discard(websocket)
        logger.info("WebSocket client disconnected (total=%d)", len(_ws_clients))


async def _broadcast_loop():
    global _ws_clients
    while True:
        await asyncio.sleep(PUSH_INTERVAL)
        if not _ws_clients:
            continue
        payload = _build_payload()
        dead = set()
        for ws in list(_ws_clients):
            try:
                await ws.send(payload)
            except Exception:
                dead.add(ws)
        _ws_clients -= dead


async def _serve_http(reader, writer):
    """Minimal HTTP server to serve dashboard static files."""
    try:
        request = await reader.read(4096)
        request_line = request.decode("utf-8", errors="ignore").split("\r\n")[0]
        method, path, *_ = request_line.split(" ")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        if path == "/" or path == "/index.html":
            file_path = os.path.join(base_dir, "index.html")
            content_type = "text/html"
        elif path.endswith(".js"):
            file_path = os.path.join(base_dir, path.lstrip("/"))
            content_type = "application/javascript"
        elif path.endswith(".css"):
            file_path = os.path.join(base_dir, path.lstrip("/"))
            content_type = "text/css"
        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        try:
            with open(file_path, "rb") as f:
                body = f.read()
            response = (
                f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n"
                f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
            ).encode() + body
        except FileNotFoundError:
            response = b"HTTP/1.1 404 Not Found\r\n\r\n"

        writer.write(response)
        await writer.drain()
        writer.close()
    except Exception as exc:
        logger.debug("HTTP handler error: %s", exc)


async def _main_async():
    global _ws_loop
    _ws_loop = asyncio.get_running_loop()

    ws_server = await serve(_ws_handler, WS_HOST, WS_PORT)
    logger.info("WebSocket server listening on ws://%s:%d", WS_HOST, WS_PORT)

    http_server = await asyncio.start_server(_serve_http, WS_HOST, HTTP_PORT)
    logger.info("HTTP server listening on http://%s:%d", WS_HOST, HTTP_PORT)

    await asyncio.gather(
        ws_server.wait_closed(),
        http_server.serve_forever(),
        _broadcast_loop(),
    )


def main():
    logger.info("SmartPitch Dashboard starting...")

    mqtt_thread = threading.Thread(target=_start_mqtt, daemon=True, name="mqtt-dashboard")
    mqtt_thread.start()

    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        logger.info("Dashboard interrupted")


if __name__ == "__main__":
    main()
