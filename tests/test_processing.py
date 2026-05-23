"""Tests for processing layer: FeatureExtractor, DataPipeline."""
import time
import pytest
from unittest.mock import MagicMock, patch
from processing.feature_extractor import FeatureExtractor, get_zone, compute_distance
from processing.data_pipeline import DataPipeline


class TestGetZone:
    def test_defense_zone(self):
        assert get_zone(0) == "defense"
        assert get_zone(10) == "defense"
        assert get_zone(34.9) == "defense"

    def test_milieu_zone(self):
        assert get_zone(35) == "milieu"
        assert get_zone(52) == "milieu"
        assert get_zone(69.9) == "milieu"

    def test_attaque_zone(self):
        assert get_zone(70) == "attaque"
        assert get_zone(90) == "attaque"
        assert get_zone(105) == "attaque"


class TestComputeDistance:
    def test_same_point_is_zero(self):
        assert compute_distance(0, 0, 0, 0) == 0.0

    def test_horizontal_distance(self):
        assert abs(compute_distance(0, 0, 3, 0) - 3.0) < 1e-9

    def test_pythagorean(self):
        assert abs(compute_distance(0, 0, 3, 4) - 5.0) < 1e-9


class TestFeatureExtractor:
    def setup_method(self):
        self.extractor = FeatureExtractor()

    def _make_frame(self, player_id=7, x=42.3, y=31.7, speed=5.2, hr=152, fatigue=0.74):
        return {
            "player_id": player_id,
            "match_id": "match_001",
            "timestamp": time.time(),
            "x": x, "y": y,
            "speed": speed,
            "heart_rate": hr,
            "fatigue": fatigue,
        }

    def test_zone_field_added(self):
        frame = self._make_frame(x=42.3)
        result = self.extractor.extract(frame)
        assert "zone" in result
        assert result["zone"] == "milieu"

    def test_first_frame_distance_step_zero(self):
        frame = self._make_frame()
        result = self.extractor.extract(frame)
        assert result["distance_step"] == 0.0

    def test_cumulative_distance_accumulates(self):
        f1 = self._make_frame(x=0, y=0)
        f2 = self._make_frame(x=3, y=4)
        f3 = self._make_frame(x=6, y=8)
        self.extractor.extract(f1)
        r2 = self.extractor.extract(f2)
        r3 = self.extractor.extract(f3)
        assert abs(r2["distance_step"] - 5.0) < 0.01
        assert abs(r3["cumulative_distance"] - 10.0) < 0.01

    def test_original_fields_preserved(self):
        frame = self._make_frame()
        result = self.extractor.extract(frame)
        for key in ("player_id", "match_id", "timestamp", "x", "y", "speed", "heart_rate", "fatigue"):
            assert key in result

    def test_reset_clears_state(self):
        f1 = self._make_frame(x=0, y=0)
        f2 = self._make_frame(x=3, y=4)
        self.extractor.extract(f1)
        self.extractor.reset(player_id=7)
        r = self.extractor.extract(f2)
        assert r["distance_step"] == 0.0

    def test_bad_frame_does_not_raise(self):
        result = self.extractor.extract({"bad": "frame"})
        assert result == {"bad": "frame"}

    def test_multiple_players_independent(self):
        f_p1 = {"player_id": 1, "match_id": "m", "timestamp": 0, "x": 0, "y": 0, "speed": 0, "heart_rate": 70, "fatigue": 0}
        f_p2 = {"player_id": 2, "match_id": "m", "timestamp": 0, "x": 50, "y": 50, "speed": 0, "heart_rate": 70, "fatigue": 0}
        self.extractor.extract(f_p1)
        self.extractor.extract(f_p2)
        r1 = self.extractor.extract({**f_p1, "x": 3, "y": 4})
        r2 = self.extractor.extract({**f_p2, "x": 53, "y": 54})
        assert abs(r1["distance_step"] - 5.0) < 0.01
        assert abs(r2["distance_step"] - 5.0) < 0.01


class TestDataPipeline:
    def test_consumer_receives_enriched_frame(self):
        received = []
        pipeline = DataPipeline()
        pipeline.register_consumer(received.append)
        pipeline.start()

        frame = {
            "player_id": 1, "match_id": "match_001", "timestamp": time.time(),
            "x": 42.0, "y": 20.0, "speed": 3.0, "heart_rate": 140, "fatigue": 0.4,
        }
        pipeline.ingest(frame)
        time.sleep(0.2)
        pipeline.stop()

        assert len(received) == 1
        assert "zone" in received[0]
        assert "cumulative_distance" in received[0]

    def test_queue_full_does_not_crash(self):
        pipeline = DataPipeline()
        pipeline._queue.maxsize = 2
        pipeline.start()
        for _ in range(10):
            pipeline.ingest({"player_id": 1, "match_id": "m", "timestamp": time.time(),
                             "x": 0, "y": 0, "speed": 0, "heart_rate": 70, "fatigue": 0})
        time.sleep(0.3)
        pipeline.stop()

    def test_multiple_consumers_called(self):
        calls_a = []
        calls_b = []
        pipeline = DataPipeline()
        pipeline.register_consumer(calls_a.append)
        pipeline.register_consumer(calls_b.append)
        pipeline.start()
        pipeline.ingest({"player_id": 1, "match_id": "m", "timestamp": time.time(),
                         "x": 10, "y": 10, "speed": 1, "heart_rate": 80, "fatigue": 0.1})
        time.sleep(0.2)
        pipeline.stop()
        assert len(calls_a) == 1
        assert len(calls_b) == 1
