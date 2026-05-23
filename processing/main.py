import sys
import signal
import logging

sys.path.insert(0, "/app")

from communication.mqtt_subscriber import MQTTSubscriber
from communication.mqtt_publisher import MQTTPublisher
from communication.config_broker import MATCH_ID, get_player_topic, MQTT_QOS
from data_pipeline import DataPipeline
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ENRICHED_TOPIC_PATTERN = "smartpitch/match/{match_id}/player/{player_id}/enriched"


def main():
    logger.info("SmartPitch Processing starting...")

    # Publisher re-publishes enriched frames on a separate topic so analytics can consume
    publisher = MQTTPublisher(match_id=MATCH_ID)
    publisher.connect()

    pipeline = DataPipeline()

    def forward_enriched(enriched_frame: dict) -> None:
        player_id = enriched_frame.get("player_id")
        topic = ENRICHED_TOPIC_PATTERN.format(match_id=MATCH_ID, player_id=player_id)
        publisher._client.publish(topic, json.dumps(enriched_frame), qos=MQTT_QOS)

    pipeline.register_consumer(forward_enriched)
    pipeline.start()

    subscriber = MQTTSubscriber(on_message_callback=pipeline.ingest, match_id=MATCH_ID)
    subscriber.connect()

    def shutdown(sig, frame):
        logger.info("Shutting down processing...")
        pipeline.stop()
        subscriber.disconnect()
        publisher.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Processing running — waiting for frames...")
    signal.pause()


if __name__ == "__main__":
    main()
