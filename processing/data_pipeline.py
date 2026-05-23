import queue
import logging
import threading
from feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class DataPipeline:
    """Receives raw MQTT frames, enriches them, and dispatches to registered consumers."""

    def __init__(self):
        self._extractor = FeatureExtractor()
        self._consumers: list = []
        self._queue: queue.Queue = queue.Queue(maxsize=1000)
        self._running = False
        self._worker_thread: threading.Thread | None = None

    def register_consumer(self, callback) -> None:
        """Register a callable that receives enriched frames."""
        self._consumers.append(callback)

    def ingest(self, raw_frame: dict) -> None:
        """Called by the MQTT subscriber callback — non-blocking enqueue."""
        try:
            self._queue.put_nowait(raw_frame)
        except queue.Full:
            logger.warning("Pipeline queue full, dropping frame for player %s", raw_frame.get("player_id"))

    def start(self) -> None:
        """Start the background processing thread."""
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_loop, daemon=True, name="pipeline-worker")
        self._worker_thread.start()
        logger.info("DataPipeline started")

    def stop(self) -> None:
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=3)
        logger.info("DataPipeline stopped")

    def _process_loop(self) -> None:
        while self._running:
            try:
                raw_frame = self._queue.get(timeout=0.5)
                enriched = self._extractor.extract(raw_frame)
                for consumer in self._consumers:
                    try:
                        consumer(enriched)
                    except Exception as exc:
                        logger.error("Consumer error: %s", exc)
            except queue.Empty:
                continue
            except Exception as exc:
                logger.error("Pipeline worker error: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def printer(frame):
        logger.info("Enriched frame: player=%s zone=%s cum_dist=%.2f",
                    frame.get("player_id"), frame.get("zone"), frame.get("cumulative_distance", 0))

    pipeline = DataPipeline()
    pipeline.register_consumer(printer)
    pipeline.start()

    import time
    for i in range(5):
        pipeline.ingest({"player_id": 1, "match_id": "match_001", "timestamp": time.time(),
                         "x": 10.0 + i * 5, "y": 20.0, "speed": 3.5 + i * 0.5,
                         "heart_rate": 140 + i, "fatigue": 0.3 + i * 0.02})
        time.sleep(0.05)
    time.sleep(0.5)
    pipeline.stop()
