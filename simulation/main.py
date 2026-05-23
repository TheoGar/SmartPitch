import sys
import logging

sys.path.insert(0, "/app")

from communication.mqtt_publisher import MQTTPublisher
from simulation_engine import SimulationEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    logger.info("SmartPitch Simulation starting...")
    publisher = MQTTPublisher()
    publisher.connect()
    engine = SimulationEngine(publisher=publisher)
    try:
        engine.run()
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    finally:
        publisher.disconnect()


if __name__ == "__main__":
    main()
