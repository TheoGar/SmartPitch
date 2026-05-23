import logging
from typing import Optional

logger = logging.getLogger(__name__)

FIELD_WIDTH = 105.0
FIELD_HEIGHT = 68.0

ZONE_DEFENSE_MAX = 35.0
ZONE_MILIEU_MAX = 70.0


def get_zone(x: float) -> str:
    """Return field zone name from x coordinate."""
    if x < ZONE_DEFENSE_MAX:
        return "defense"
    elif x < ZONE_MILIEU_MAX:
        return "milieu"
    return "attaque"


def compute_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance between two field positions."""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


class FeatureExtractor:
    """Computes derived features (zone, cumulative distance) for each player."""

    def __init__(self):
        self._last_positions: dict[int, tuple[float, float]] = {}
        self._cumulative_distance: dict[int, float] = {}

    def extract(self, frame: dict) -> dict:
        """Enrich a raw sensor frame with computed features. Returns enriched dict."""
        try:
            player_id = frame["player_id"]
            x = float(frame["x"])
            y = float(frame["y"])

            zone = get_zone(x)

            last = self._last_positions.get(player_id)
            if last is not None:
                dist_step = compute_distance(last[0], last[1], x, y)
            else:
                dist_step = 0.0

            self._last_positions[player_id] = (x, y)
            prev_cumulative = self._cumulative_distance.get(player_id, 0.0)
            self._cumulative_distance[player_id] = prev_cumulative + dist_step

            enriched = dict(frame)
            enriched["zone"] = zone
            enriched["distance_step"] = round(dist_step, 3)
            enriched["cumulative_distance"] = round(self._cumulative_distance[player_id], 2)
            return enriched
        except (KeyError, ValueError, TypeError) as exc:
            logger.error("Feature extraction failed: %s | frame=%s", exc, frame)
            return frame

    def reset(self, player_id: Optional[int] = None) -> None:
        """Reset state for one or all players."""
        if player_id is None:
            self._last_positions.clear()
            self._cumulative_distance.clear()
        else:
            self._last_positions.pop(player_id, None)
            self._cumulative_distance.pop(player_id, None)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    extractor = FeatureExtractor()
    frame1 = {"player_id": 7, "match_id": "match_001", "timestamp": 1.0, "x": 42.3, "y": 31.7,
               "speed": 5.2, "heart_rate": 152, "fatigue": 0.74}
    frame2 = {"player_id": 7, "match_id": "match_001", "timestamp": 1.1, "x": 45.0, "y": 33.0,
               "speed": 5.5, "heart_rate": 153, "fatigue": 0.75}
    logger.info("Frame 1: %s", extractor.extract(frame1))
    logger.info("Frame 2: %s", extractor.extract(frame2))
