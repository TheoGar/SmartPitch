"""Tests for analytics layer: HeatmapGenerator, EventDetector."""
import time
import pytest
import numpy as np
from analytics.heatmap_generator import HeatmapGenerator, GRID_ROWS, GRID_COLS
from analytics.event_detector import (
    EventDetector,
    FATIGUE_THRESHOLD, SPRINT_SPEED, HIGH_HR_THRESHOLD, INACTIVITY_DISTANCE,
)


class TestHeatmapGenerator:
    def setup_method(self):
        self.hm = HeatmapGenerator()

    def test_initial_grid_is_zero(self):
        grid = np.array(self.hm.get_collective())
        assert grid.sum() == 0

    def test_update_increments_cell(self):
        self.hm.update(player_id=1, x=0.0, y=0.0)
        grid = np.array(self.hm.get_collective())
        assert grid.sum() == 1

    def test_grid_shape(self):
        grid = self.hm.get_collective()
        assert len(grid) == GRID_ROWS
        assert len(grid[0]) == GRID_COLS

    def test_multiple_updates_accumulate(self):
        for _ in range(5):
            self.hm.update(player_id=1, x=10.0, y=10.0)
        grid = np.array(self.hm.get_collective())
        assert grid.sum() == 5

    def test_per_player_grid_is_independent(self):
        self.hm.update(player_id=1, x=10.0, y=10.0)
        self.hm.update(player_id=2, x=80.0, y=60.0)
        g1 = np.array(self.hm.get_player(1))
        g2 = np.array(self.hm.get_player(2))
        assert g1.sum() == 1
        assert g2.sum() == 1
        # Both players in different cells
        assert not np.array_equal(g1, g2)

    def test_boundary_positions_clamped(self):
        self.hm.update(player_id=1, x=105.0, y=68.0)
        grid = np.array(self.hm.get_collective())
        assert grid.sum() == 1

    def test_reset_clears_all(self):
        self.hm.update(1, 10, 10)
        self.hm.update(2, 50, 30)
        self.hm.reset()
        assert np.array(self.hm.get_collective()).sum() == 0

    def test_collective_is_sum_of_all_players(self):
        self.hm.update(1, 0, 0)
        self.hm.update(2, 0, 0)
        collective = np.array(self.hm.get_collective())
        p1 = np.array(self.hm.get_player(1))
        p2 = np.array(self.hm.get_player(2))
        assert collective.sum() == p1.sum() + p2.sum()

    def test_get_player_unknown_returns_zeros(self):
        grid = np.array(self.hm.get_player(999))
        assert grid.sum() == 0
        assert grid.shape == (GRID_ROWS, GRID_COLS)


class TestEventDetector:
    def setup_method(self):
        self.detector = EventDetector()

    def _frame(self, player_id=1, fatigue=0.5, speed=3.0, hr=140, cum_dist=0.0, ts=None):
        return {
            "player_id": player_id,
            "fatigue": fatigue,
            "speed": speed,
            "heart_rate": hr,
            "cumulative_distance": cum_dist,
            "timestamp": ts or time.time(),
        }

    def test_no_alerts_normal_values(self):
        alerts = self.detector.detect(self._frame(fatigue=0.5, speed=3.0, hr=140))
        assert alerts == []

    def test_fatigue_alert_triggered(self):
        alerts = self.detector.detect(self._frame(fatigue=FATIGUE_THRESHOLD + 0.01))
        assert "fatigue" in alerts

    def test_fatigue_alert_not_triggered_below_threshold(self):
        alerts = self.detector.detect(self._frame(fatigue=FATIGUE_THRESHOLD - 0.01))
        assert "fatigue" not in alerts

    def test_sprint_alert_triggered(self):
        alerts = self.detector.detect(self._frame(speed=SPRINT_SPEED + 0.1))
        assert "sprint" in alerts

    def test_sprint_alert_not_triggered_below_threshold(self):
        alerts = self.detector.detect(self._frame(speed=SPRINT_SPEED - 0.1))
        assert "sprint" not in alerts

    def test_high_hr_alert_triggered(self):
        alerts = self.detector.detect(self._frame(hr=HIGH_HR_THRESHOLD + 1))
        assert "high_hr" in alerts

    def test_high_hr_alert_not_triggered_below(self):
        alerts = self.detector.detect(self._frame(hr=HIGH_HR_THRESHOLD - 1))
        assert "high_hr" not in alerts

    def test_multiple_alerts_combined(self):
        alerts = self.detector.detect(self._frame(
            fatigue=FATIGUE_THRESHOLD + 0.1,
            speed=SPRINT_SPEED + 1,
            hr=HIGH_HR_THRESHOLD + 10,
        ))
        assert "fatigue" in alerts
        assert "sprint" in alerts
        assert "high_hr" in alerts

    def test_inactivity_detected_after_window(self):
        now = time.time()
        # Feed frames spanning 31 seconds with minimal distance change
        for i in range(32):
            self.detector.detect(self._frame(player_id=5, cum_dist=0.0, ts=now + i))
        alerts = self.detector.detect(self._frame(player_id=5, cum_dist=1.0, ts=now + 32))
        assert "inactivity" in alerts

    def test_no_inactivity_if_sufficient_distance(self):
        now = time.time()
        for i in range(32):
            self.detector.detect(self._frame(player_id=6, cum_dist=float(i * 0.5), ts=now + i))
        alerts = self.detector.detect(self._frame(player_id=6, cum_dist=16.0, ts=now + 32))
        assert "inactivity" not in alerts

    def test_frame_without_player_id_returns_empty(self):
        alerts = self.detector.detect({"fatigue": 0.9, "speed": 10.0, "heart_rate": 200})
        assert alerts == []
