"""Tests for simulation layer: PlayerState, VirtualSensor."""
import time
import pytest
from unittest.mock import MagicMock, patch
from simulation.virtual_sensors import VirtualSensor, FIELD_WIDTH, FIELD_HEIGHT
from simulation.simulation_engine import PlayerState, SimulationEngine


class TestVirtualSensor:
    def setup_method(self):
        self.sensor = VirtualSensor(player_id=7, match_id="match_test")

    def test_build_frame_fields(self):
        frame = self.sensor.build_frame(x=42.3, y=31.7, speed=5.2, heart_rate=152, fatigue=0.74)
        assert frame["player_id"] == 7
        assert frame["match_id"] == "match_test"
        assert frame["x"] == 42.3
        assert frame["y"] == 31.7
        assert frame["speed"] == 5.2
        assert frame["heart_rate"] == 152
        assert frame["fatigue"] == 0.74
        assert "timestamp" in frame
        assert isinstance(frame["timestamp"], float)

    def test_build_frame_timestamp_recent(self):
        before = time.time()
        frame = self.sensor.build_frame(x=0, y=0, speed=0, heart_rate=70, fatigue=0.0)
        after = time.time()
        assert before <= frame["timestamp"] <= after

    def test_to_json_is_valid(self):
        import json
        frame = self.sensor.build_frame(x=10, y=20, speed=3, heart_rate=120, fatigue=0.5)
        result = self.sensor.to_json(frame)
        parsed = json.loads(result)
        assert parsed["player_id"] == 7

    def test_build_frame_rounding(self):
        frame = self.sensor.build_frame(x=42.3456, y=31.7891, speed=5.2345, heart_rate=152, fatigue=0.74321)
        assert frame["x"] == round(42.3456, 2)
        assert frame["y"] == round(31.7891, 2)
        assert frame["speed"] == round(5.2345, 2)
        assert frame["fatigue"] == round(0.74321, 3)


class TestPlayerState:
    def setup_method(self):
        self.player = PlayerState(player_id=1)

    def test_initial_position_in_field(self):
        assert 0 <= self.player.x <= FIELD_WIDTH
        assert 0 <= self.player.y <= FIELD_HEIGHT

    def test_initial_fatigue_in_range(self):
        assert 0.0 <= self.player.fatigue <= 1.0

    def test_update_keeps_position_in_field(self):
        for _ in range(50):
            self.player.update(dt=0.1)
            assert 0 <= self.player.x <= FIELD_WIDTH, f"x={self.player.x} out of bounds"
            assert 0 <= self.player.y <= FIELD_HEIGHT, f"y={self.player.y} out of bounds"

    def test_fatigue_increases_over_time(self):
        initial_fatigue = self.player.fatigue
        for _ in range(100):
            self.player.update(dt=0.1)
        assert self.player.fatigue >= initial_fatigue

    def test_fatigue_never_exceeds_one(self):
        for _ in range(10000):
            self.player.update(dt=0.1)
        assert self.player.fatigue <= 1.0

    def test_speed_is_non_negative(self):
        for _ in range(20):
            self.player.update(dt=0.1)
            assert self.player.speed >= 0

    def test_heart_rate_in_range(self):
        for _ in range(50):
            self.player.update(dt=0.1)
        assert PlayerState.HR_BASE <= self.player.heart_rate <= PlayerState.HR_MAX


class TestSimulationEngine:
    def test_engine_initialises_correct_number_of_players(self):
        mock_publisher = MagicMock()
        engine = SimulationEngine(publisher=mock_publisher, num_players=5, match_id="m1")
        assert len(engine.players) == 5

    def test_engine_calls_publish(self):
        mock_publisher = MagicMock()
        engine = SimulationEngine(publisher=mock_publisher, num_players=2, match_id="m1")
        engine.match_duration = 0  # exit after first iteration check
        # Manually run one tick
        for player in engine.players:
            player.update(0.1)
            sensor = engine.sensors[player.player_id]
            frame = sensor.build_frame(player.x, player.y, player.speed, player.heart_rate, player.fatigue)
            engine.publisher.publish(player.player_id, frame)
        assert mock_publisher.publish.call_count == 2
