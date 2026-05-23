import os
import time
import random
import logging
import numpy as np
from virtual_sensors import VirtualSensor

logger = logging.getLogger(__name__)

FIELD_WIDTH = 105.0
FIELD_HEIGHT = 68.0
PUBLISH_INTERVAL = 0.1  # 100ms

NUM_PLAYERS = int(os.getenv("PLAYERS", 10))
MATCH_DURATION_MIN = int(os.getenv("MATCH_DURATION", 90))
MATCH_ID = os.getenv("MATCH_ID", "match_001")


class PlayerState:
    """Holds and updates the simulated state of a single player."""

    BASE_SPEED_MS = 3.5
    MAX_SPEED_MS = 9.0
    FATIGUE_RATE = 0.0001
    HR_BASE = 70
    HR_MAX = 200

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.x = random.uniform(5.0, FIELD_WIDTH - 5.0)
        self.y = random.uniform(5.0, FIELD_HEIGHT - 5.0)
        self.vx = random.uniform(-2.0, 2.0)
        self.vy = random.uniform(-2.0, 2.0)
        self.fatigue = random.uniform(0.0, 0.1)
        self.heart_rate = self.HR_BASE + random.randint(0, 30)
        self._sprint_timer = 0.0
        self._direction_timer = random.uniform(0, 3.0)

    def update(self, dt: float) -> None:
        """Advance player simulation by dt seconds."""
        self._direction_timer -= dt
        if self._direction_timer <= 0:
            self._change_direction()
            self._direction_timer = random.uniform(1.5, 5.0)

        self._sprint_timer -= dt
        is_sprinting = self._sprint_timer > 0

        speed_factor = 1.5 if is_sprinting else 1.0
        max_v = self.MAX_SPEED_MS * speed_factor
        effective_v = self.BASE_SPEED_MS * (1.0 - self.fatigue * 0.5) * speed_factor

        speed_norm = np.hypot(self.vx, self.vy)
        if speed_norm > 0:
            self.vx = self.vx / speed_norm * effective_v
            self.vy = self.vy / speed_norm * effective_v

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Bounce off boundaries
        if self.x < 0 or self.x > FIELD_WIDTH:
            self.vx = -self.vx
            self.x = max(0.0, min(FIELD_WIDTH, self.x))
        if self.y < 0 or self.y > FIELD_HEIGHT:
            self.vy = -self.vy
            self.y = max(0.0, min(FIELD_HEIGHT, self.y))

        self.fatigue = min(1.0, self.fatigue + self.FATIGUE_RATE * dt * (1.5 if is_sprinting else 1.0))

        target_hr = self.HR_BASE + int((self.HR_MAX - self.HR_BASE) * (0.3 + self.fatigue * 0.7))
        self.heart_rate += int((target_hr - self.heart_rate) * 0.05)
        self.heart_rate = max(self.HR_BASE, min(self.HR_MAX, self.heart_rate))

    def _change_direction(self) -> None:
        angle = random.uniform(0, 2 * np.pi)
        self.vx = np.cos(angle)
        self.vy = np.sin(angle)
        if random.random() < 0.15:
            self._sprint_timer = random.uniform(1.5, 4.0)

    @property
    def speed(self) -> float:
        return float(np.hypot(self.vx, self.vy))


class SimulationEngine:
    """Runs the full match simulation for all players."""

    def __init__(self, publisher, num_players: int = NUM_PLAYERS, match_id: str = MATCH_ID):
        self.publisher = publisher
        self.match_id = match_id
        self.players = [PlayerState(pid) for pid in range(1, num_players + 1)]
        self.sensors = {p.player_id: VirtualSensor(p.player_id, match_id) for p in self.players}
        self.match_start = time.time()
        self.match_duration = MATCH_DURATION_MIN * 60

    def run(self) -> None:
        """Main simulation loop — runs until match duration elapses."""
        logger.info("Simulation started: %d players, match_id=%s", len(self.players), self.match_id)
        last_tick = time.time()

        while True:
            now = time.time()
            elapsed = now - self.match_start
            if elapsed >= self.match_duration:
                logger.info("Match finished after %.0f seconds.", elapsed)
                break

            dt = now - last_tick
            last_tick = now

            for player in self.players:
                try:
                    player.update(dt)
                    sensor = self.sensors[player.player_id]
                    frame = sensor.build_frame(
                        x=player.x,
                        y=player.y,
                        speed=player.speed,
                        heart_rate=player.heart_rate,
                        fatigue=player.fatigue,
                    )
                    self.publisher.publish(player.player_id, frame)
                except Exception as exc:
                    logger.error("Error updating player %d: %s", player.player_id, exc)

            time.sleep(PUBLISH_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from communication.mqtt_publisher import MQTTPublisher  # noqa: F401

    publisher = MQTTPublisher()
    publisher.connect()
    engine = SimulationEngine(publisher=publisher)
    engine.run()
