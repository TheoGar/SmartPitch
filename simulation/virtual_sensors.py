import time
import json
import logging

logger = logging.getLogger(__name__)

FIELD_WIDTH = 105.0
FIELD_HEIGHT = 68.0


class VirtualSensor:
    """Produces sensor JSON frames for a single player at regular intervals."""

    def __init__(self, player_id: int, match_id: str):
        self.player_id = player_id
        self.match_id = match_id

    def build_frame(self, x: float, y: float, speed: float, heart_rate: int, fatigue: float) -> dict:
        """Build a sensor data frame from current player state."""
        return {
            "player_id": self.player_id,
            "match_id": self.match_id,
            "timestamp": time.time(),
            "x": round(x, 2),
            "y": round(y, 2),
            "speed": round(speed, 2),
            "heart_rate": heart_rate,
            "fatigue": round(fatigue, 3),
        }

    def to_json(self, frame: dict) -> str:
        return json.dumps(frame)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sensor = VirtualSensor(player_id=1, match_id="match_001")
    frame = sensor.build_frame(x=42.3, y=31.7, speed=5.2, heart_rate=152, fatigue=0.74)
    logger.info("Sample frame: %s", sensor.to_json(frame))
