"""Focused tests for keyboard routing into the existing human movement logic."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import app
from core.maze import Maze
from ui.keyboard_component import direction_for_key


class KeyboardControlTests(unittest.TestCase):
    def test_arrow_and_wasd_mapping(self) -> None:
        expected = {
            "ArrowUp": (-1, 0), "w": (-1, 0), "W": (-1, 0),
            "ArrowDown": (1, 0), "s": (1, 0), "S": (1, 0),
            "ArrowLeft": (0, -1), "a": (0, -1), "A": (0, -1),
            "ArrowRight": (0, 1), "d": (0, 1), "D": (0, 1),
        }
        for key, direction in expected.items():
            self.assertEqual(direction_for_key(key), direction)

    def test_keyboard_uses_existing_move_function(self) -> None:
        state = SimpleNamespace(human_active=True, last_keyboard_event=None)
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event({"key": "ArrowRight", "id": "event-1"})
            move.assert_called_once_with((0, 1))

    def test_duplicate_event_is_not_replayed(self) -> None:
        state = SimpleNamespace(human_active=True, last_keyboard_event=None)
        event = {"key": "w", "id": "event-1"}
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event(event)
            app.handle_keyboard_event(event)
            move.assert_called_once_with((-1, 0))

    def test_keyboard_is_disabled_outside_active_attempt(self) -> None:
        state = SimpleNamespace(human_active=False, last_keyboard_event=None)
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event({"key": "d", "id": "event-1"})
            move.assert_not_called()

    def test_existing_movement_blocks_walls_and_boundaries(self) -> None:
        maze = Maze(3, 3, (0, 0), (2, 2), {(0, 1)})
        state = SimpleNamespace(
            human_active=True,
            sim_maze=maze,
            human_path=[maze.start],
            human_started=0.0,
            human_result=None,
        )
        with patch.object(app.st, "session_state", state):
            app.move_human((-1, 0))  # Outside the grid.
            app.move_human((0, 1))   # Wall.
        self.assertEqual(state.human_path, [(0, 0)])

    def test_existing_movement_updates_path_and_finishes_at_goal(self) -> None:
        maze = Maze(2, 2, (0, 0), (0, 1))
        state = SimpleNamespace(
            human_active=True,
            sim_maze=maze,
            human_path=[maze.start],
            human_started=0.0,
            human_result=None,
        )
        with patch.object(app.st, "session_state", state), patch.object(
            app.time, "perf_counter", return_value=1.0
        ):
            app.move_human((0, 1))
        self.assertEqual(state.human_path, [(0, 0), (0, 1)])
        self.assertFalse(state.human_active)
        self.assertEqual(state.human_result["Path Length"], 1)
        self.assertEqual(state.human_result["Path Cost"], 1)


if __name__ == "__main__":
    unittest.main()
