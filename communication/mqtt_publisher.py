import json
import time
import uuid
import logging
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from communication.config_broker import (
    MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, MQTT_QOS,
    MATCH_ID, get_player_topic,
)

logger = logging.getLogger(__name__)

RECONNECT_DELAY_MIN = 1
RECONNECT_DELAY_MAX = 60


class MQTTPublisher:
    """Publishes player sensor frames to the MQTT broker with auto-reconnect."""

    def __init__(self, match_id: str = MATCH_ID, client_suffix: str = ""):
        self.match_id = match_id
        self._connected = False
        self._loop_started = False
        unique_id = client_suffix or uuid.uuid4().hex[:8]
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=f"smartpitch-pub-{unique_id}",
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected = True
            logger.info("Publisher connected to %s:%d", MQTT_BROKER, MQTT_PORT)
        else:
            logger.warning("Publisher connection refused: reason_code=%s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        logger.warning("Publisher disconnected (reason_code=%s)", reason_code)

    def connect(self) -> None:
        """Connect to broker with exponential backoff retry."""
        delay = RECONNECT_DELAY_MIN
        while True:
            try:
                self._client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
                if not self._loop_started:
                    self._client.loop_start()
                    self._loop_started = True
                # Wait up to 5 s for the connection callback
                deadline = time.time() + 5
                while not self._connected and time.time() < deadline:
                    time.sleep(0.1)
                if self._connected:
                    return
                raise ConnectionError("Broker did not confirm connection in time")
            except Exception as exc:
                logger.error("Cannot connect to broker: %s — retrying in %ds", exc, delay)
                time.sleep(delay)
                delay = min(delay * 2, RECONNECT_DELAY_MAX)

    def publish(self, player_id: int, frame: dict) -> None:
        """Publish a single player frame. Reconnects automatically if needed."""
        if not self._connected:
            logger.warning("Publisher not connected, attempting reconnect...")
            self.connect()
        topic = get_player_topic(self.match_id, player_id)
        payload = json.dumps(frame)
        result = self._client.publish(topic, payload, qos=MQTT_QOS)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("Publish failed for player %d: rc=%d", player_id, result.rc)

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("Publisher disconnected cleanly")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    import sys
    sys.path.insert(0, "/app")
    pub = MQTTPublisher()
    pub.connect()
    sample = {"player_id": 1, "match_id": MATCH_ID, "timestamp": time.time(),
              "x": 42.3, "y": 31.7, "speed": 5.2, "heart_rate": 152, "fatigue": 0.74}
    pub.publish(1, sample)
    logger.info("Test frame published")
    pub.disconnect()
