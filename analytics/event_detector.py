import os
import time
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

FATIGUE_THRESHOLD = float(os.getenv("FATIGUE_THRESHOLD", 0.80))
INACTIVITY_DISTANCE = float(os.getenv("INACTIVITY_DISTANCE", 5.0))
INACTIVITY_WINDOW = 30.0  # seconds
SPRINT_SPEED = float(os.getenv("SPRINT_SPEED", 7.0))
HIGH_HR_THRESHOLD = int(os.getenv("HIGH_HR_THRESHOLD", 170))


class EventDetector:
    """Detects game events by threshold rules on enriched frames."""

    def __init__(self):
        # Sliding window of (timestamp, cumulative_distance) per player
        self._distance_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=500))

    def detect(self, frame: dict) -> list[str]:
        """Return list of alert strings for this frame. Empty if nothing triggered."""
        alerts = []
        player_id = frame.get("player_id")
        if player_id is None:
            return alerts

        fatigue = frame.get("fatigue", 0.0)
        speed = frame.get("speed", 0.0)
        heart_rate = frame.get("heart_rate", 0)
        cumulative_distance = frame.get("cumulative_distance", 0.0)
        timestamp = frame.get("timestamp", time.time())

        if fatigue > FATIGUE_THRESHOLD:
            alerts.append("fatigue")

        if speed > SPRINT_SPEED:
            alerts.append("sprint")

        if heart_rate > HIGH_HR_THRESHOLD:
            alerts.append("high_hr")

        # Inactivity: distance covered over last INACTIVITY_WINDOW seconds < threshold
        history = self._distance_history[player_id]
        history.append((timestamp, cumulative_distance))

        window_start = timestamp - INACTIVITY_WINDOW
        old_entries = [(t, d) for t, d in history if t >= window_start]
        if len(old_entries) >= 2:
            dist_in_window = old_entries[-1][1] - old_entries[0][1]
            if dist_in_window < INACTIVITY_DISTANCE:
                alerts.append("inactivity")

        return alerts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = EventDetector()
    frame = {
        "player_id": 7, "timestamp": time.time(), "fatigue": 0.85,
        "speed": 8.1, "heart_rate": 175, "cumulative_distance": 100.0,
    }
    alerts = detector.detect(frame)
    logger.info("Alerts detected: %s", alerts)
