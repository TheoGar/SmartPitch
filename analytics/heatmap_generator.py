import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

FIELD_WIDTH = 105.0
FIELD_HEIGHT = 68.0
GRID_COLS = 21   # 105 / 5
GRID_ROWS = 14   # 68 / 5
CELL_W = FIELD_WIDTH / GRID_COLS
CELL_H = FIELD_HEIGHT / GRID_ROWS

NUM_PLAYERS = int(os.getenv("PLAYERS", 10))
_HALF = NUM_PLAYERS // 2

# Players 1..half → team A, (half+1)..N → team B
TEAM_A_IDS = set(range(1, _HALF + 1))
TEAM_B_IDS = set(range(_HALF + 1, NUM_PLAYERS + 1))
GOALKEEPER_A = 1
GOALKEEPER_B = _HALF + 1


def get_team(player_id: int) -> str:
    return "A" if player_id in TEAM_A_IDS else "B"


def is_goalkeeper(player_id: int) -> bool:
    return player_id in (GOALKEEPER_A, GOALKEEPER_B)


class HeatmapGenerator:
    """Accumulates player positions into persistent occupancy grids (21×14).

    Tracks collective, per-team (A/B), and per-player grids.
    Updates by accumulation — never recalculated from zero.
    """

    def __init__(self):
        self._collective: np.ndarray = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.int32)
        self._team_a: np.ndarray = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.int32)
        self._team_b: np.ndarray = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.int32)
        self._per_player: dict[int, np.ndarray] = {}

    def _coords_to_cell(self, x: float, y: float) -> tuple[int, int]:
        col = int(min(x / CELL_W, GRID_COLS - 1))
        row = int(min(y / CELL_H, GRID_ROWS - 1))
        return max(0, row), max(0, col)

    def update(self, player_id: int, x: float, y: float) -> None:
        """Register one position observation."""
        try:
            row, col = self._coords_to_cell(x, y)
            self._collective[row, col] += 1
            if player_id in TEAM_A_IDS:
                self._team_a[row, col] += 1
            else:
                self._team_b[row, col] += 1
            if player_id not in self._per_player:
                self._per_player[player_id] = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.int32)
            self._per_player[player_id][row, col] += 1
        except Exception as exc:
            logger.error("Heatmap update error for player %d: %s", player_id, exc)

    def get_collective(self) -> list[list[int]]:
        return self._collective.tolist()

    def get_team_a(self) -> list[list[int]]:
        return self._team_a.tolist()

    def get_team_b(self) -> list[list[int]]:
        return self._team_b.tolist()

    def get_player(self, player_id: int) -> list[list[int]]:
        grid = self._per_player.get(player_id, np.zeros((GRID_ROWS, GRID_COLS), dtype=np.int32))
        return grid.tolist()

    def get_active_player_ids(self) -> list[int]:
        return sorted(self._per_player.keys())

    def reset(self) -> None:
        self._collective[:] = 0
        self._team_a[:] = 0
        self._team_b[:] = 0
        for grid in self._per_player.values():
            grid[:] = 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    hm = HeatmapGenerator()
    hm.update(1, 10.0, 34.0)   # GK team A
    hm.update(3, 42.3, 31.7)   # team A
    hm.update(6, 95.0, 34.0)   # GK team B
    hm.update(8, 60.0, 20.0)   # team B
    logger.info("Collective sum: %d", np.array(hm.get_collective()).sum())
    logger.info("Team A sum: %d", np.array(hm.get_team_a()).sum())
    logger.info("Team B sum: %d", np.array(hm.get_team_b()).sum())
