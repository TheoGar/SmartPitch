import sys
import signal
import logging

sys.path.insert(0, "/app")

from communication.mqtt_subscriber import MQTTSubscriber
from communication.config_broker import MATCH_ID
from heatmap_generator import HeatmapGenerator
from event_detector import EventDetector
from database.db_handler import DBHandler
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ENRICHED_TOPIC_PATTERN = f"smartpitch/match/{MATCH_ID}/player/+/enriched"

heatmap = HeatmapGenerator()
detector = EventDetector()
db = DBHandler()


def process_enriched_frame(frame: dict) -> None:
    player_id = frame.get("player_id")
    x = frame.get("x")
    y = frame.get("y")
    match_id = frame.get("match_id", MATCH_ID)
    timestamp = frame.get("timestamp", time.time())

    if x is not None and y is not None and player_id is not None:
        heatmap.update(player_id, x, y)

    alerts = detector.detect(frame)

    db.insert_frame(frame)

    for alert in alerts:
        db.insert_event(match_id, player_id, timestamp, alert)

    if alerts:
        logger.info("Player %d alerts: %s", player_id, alerts)


def main():
    logger.info("SmartPitch Analytics starting...")

    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion
    from communication.config_broker import MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, MQTT_QOS
    import json

    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id=f"smartpitch-analytics-{MATCH_ID}",
    )
    connected = [False]

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            connected[0] = True
            c.subscribe(ENRICHED_TOPIC_PATTERN, qos=MQTT_QOS)
            logger.info("Analytics subscribed to %s", ENRICHED_TOPIC_PATTERN)

    def on_message(c, userdata, message):
        try:
            frame = json.loads(message.payload.decode("utf-8"))
            process_enriched_frame(frame)
        except Exception as exc:
            logger.error("Analytics message error: %s", exc)

    client.on_connect = on_connect
    client.on_message = on_message

    delay = 1
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            client.loop_start()
            deadline = time.time() + 5
            while not connected[0] and time.time() < deadline:
                time.sleep(0.1)
            if connected[0]:
                break
        except Exception as exc:
            logger.error("Analytics cannot connect: %s — retry in %ds", exc, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)

    def shutdown(sig, frame):
        logger.info("Analytics shutting down...")
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Analytics running...")
    signal.pause()


if __name__ == "__main__":
    main()
