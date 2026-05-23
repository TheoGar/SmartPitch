import json
import time
import uuid
import logging
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from communication.config_broker import (
    MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, MQTT_QOS,
    MATCH_ID, get_subscribe_pattern,
)

logger = logging.getLogger(__name__)

RECONNECT_DELAY_MIN = 1
RECONNECT_DELAY_MAX = 60


class MQTTSubscriber:
    """Subscribes to all player topics for a match and forwards frames via a callback."""

    def __init__(self, on_message_callback, match_id: str = MATCH_ID, client_suffix: str = ""):
        self.match_id = match_id
        self.on_message_callback = on_message_callback
        self._connected = False
        self._loop_started = False
        unique_id = client_suffix or uuid.uuid4().hex[:8]
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=f"smartpitch-sub-{unique_id}",
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self._connected = True
            topic = get_subscribe_pattern(self.match_id)
            client.subscribe(topic, qos=MQTT_QOS)
            logger.info("Subscriber connected and subscribed to %s", topic)
        else:
            logger.warning("Subscriber connection refused: reason_code=%s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._connected = False
        logger.warning("Subscriber disconnected (reason_code=%s)", reason_code)
        self._reconnect()

    def _on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            self.on_message_callback(payload)
        except Exception as exc:
            logger.error("Failed to process MQTT message: %s", exc)

    def _reconnect(self) -> None:
        delay = RECONNECT_DELAY_MIN
        while not self._connected:
            try:
                logger.info("Attempting reconnect to broker in %ds...", delay)
                time.sleep(delay)
                self._client.reconnect()
                delay = RECONNECT_DELAY_MIN
            except Exception as exc:
                logger.error("Reconnect failed: %s", exc)
                delay = min(delay * 2, RECONNECT_DELAY_MAX)

    def connect(self) -> None:
        """Connect to broker with exponential backoff retry."""
        delay = RECONNECT_DELAY_MIN
        while True:
            try:
                self._client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
                if not self._loop_started:
                    self._client.loop_start()
                    self._loop_started = True
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

    def disconnect(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("Subscriber disconnected cleanly")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def handle(frame):
        logger.info("Received frame: player_id=%s speed=%.2f", frame.get("player_id"), frame.get("speed", 0))

    sub = MQTTSubscriber(on_message_callback=handle)
    sub.connect()
    try:
        import signal
        signal.pause()
    except (KeyboardInterrupt, AttributeError):
        pass
    finally:
        sub.disconnect()
