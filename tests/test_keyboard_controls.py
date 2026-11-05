"""Focused tests for keyboard routing into the existing human movement logic."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import app
from core.maze import Maze
from pathlib import Path

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

    def test_two_rapid_keys_are_processed_in_order(self) -> None:
        state = SimpleNamespace(
            human_active=True, last_keyboard_event=None,
            last_keyboard_sequence=0, keyboard_attempt_id=3,
        )
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event({
                "events": [
                    {"sequence": 1, "key": "ArrowRight"},
                    {"sequence": 2, "key": "ArrowDown"},
                ],
                "attempt": 3,
                "id": "batch-1",
            })
        self.assertEqual([call.args[0] for call in move.call_args_list], [(0, 1), (1, 0)])

    def test_five_rapid_keys_are_all_processed(self) -> None:
        state = SimpleNamespace(
            human_active=True, last_keyboard_event=None,
            last_keyboard_sequence=0, keyboard_attempt_id=4,
        )
        keys = ["w", "a", "s", "d", "ArrowUp"]
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event({
                "events": [
                    {"sequence": index, "key": key}
                    for index, key in enumerate(keys, start=1)
                ],
                "attempt": 4,
                "id": "batch-2",
            })
        self.assertEqual(
            [call.args[0] for call in move.call_args_list],
            [(-1, 0), (0, -1), (1, 0), (0, 1), (-1, 0)],
        )

    def test_mixed_rapid_sequence_preserves_exact_order(self) -> None:
        state = SimpleNamespace(
            human_active=True, last_keyboard_event=None,
            last_keyboard_sequence=0, keyboard_attempt_id=5,
        )
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event({
                "events": [
                    {"sequence": 1, "key": "ArrowRight"},
                    {"sequence": 2, "key": "ArrowRight"},
                    {"sequence": 3, "key": "ArrowDown"},
                    {"sequence": 4, "key": "ArrowLeft"},
                ],
                "attempt": 5,
                "id": "batch-mixed",
            })
        self.assertEqual(
            [call.args[0] for call in move.call_args_list],
            [(0, 1), (0, 1), (1, 0), (0, -1)],
        )

    def test_duplicate_event_is_not_replayed(self) -> None:
        state = SimpleNamespace(human_active=True, last_keyboard_event=None)
        event = {"key": "w", "id": "event-1"}
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event(event)
            app.handle_keyboard_event(event)
            move.assert_called_once_with((-1, 0))

    def test_duplicate_batch_is_not_replayed(self) -> None:
        state = SimpleNamespace(
            human_active=True, last_keyboard_event=None,
            last_keyboard_sequence=0, keyboard_attempt_id=6,
        )
        event = {
            "events": [
                {"sequence": 1, "key": "d"},
                {"sequence": 2, "key": "s"},
            ],
            "attempt": 6,
            "id": "batch-duplicate",
        }
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event(event)
            app.handle_keyboard_event(event)
        self.assertEqual(move.call_count, 2)

    def test_cumulative_batch_recovers_events_after_a_dropped_value(self) -> None:
        state = SimpleNamespace(
            human_active=True, last_keyboard_event=None,
            last_keyboard_sequence=2, keyboard_attempt_id=7,
        )
        # Simulate Streamlit dropping the intermediate value containing event
        # 3. The next cumulative value still contains events 3 and 4.
        event = {
            "events": [
                {"sequence": 1, "key": "d"},
                {"sequence": 2, "key": "d"},
                {"sequence": 3, "key": "s"},
                {"sequence": 4, "key": "a"},
            ],
            "attempt": 7,
            "id": "batch-latest",
        }
        with patch.object(app.st, "session_state", state), patch.object(app, "move_human") as move:
            app.handle_keyboard_event(event)
        self.assertEqual([call.args[0] for call in move.call_args_list], [(1, 0), (0, -1)])

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

    def test_rapid_batch_uses_validation_and_stops_at_goal(self) -> None:
        maze = Maze(3, 3, (0, 0), (1, 2), {(1, 0)})
        state = SimpleNamespace(
            human_active=True,
            last_keyboard_event=None,
            last_keyboard_sequence=0,
            keyboard_attempt_id=8,
            sim_maze=maze,
            human_path=[maze.start],
            human_started=0.0,
            human_result=None,
        )
        # Out of bounds, wall, then Right, Right, Down reaches the goal. The
        # final Left must not run after completion.
        event = {
            "events": [
                {"sequence": index, "key": key}
                for index, key in enumerate(
                    ["ArrowUp", "ArrowDown", "ArrowRight", "d", "s", "a"],
                    start=1,
                )
            ],
            "attempt": 8,
            "id": "batch-goal",
        }
        with patch.object(app.st, "session_state", state), patch.object(
            app.time, "perf_counter", return_value=2.0
        ):
            app.handle_keyboard_event(event)
        self.assertEqual(state.human_path, [(0, 0), (0, 1), (0, 2), (1, 2)])
        self.assertFalse(state.human_active)
        self.assertEqual(state.human_result["Path Length"], 3)

    def test_frontend_buffers_filters_and_serializes_input(self) -> None:
        frontend = (
            Path(app.__file__).parent / "ui" / "keyboard_frontend" / "index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("controller.history.push", frontend)
        self.assertIn("events: this.history.slice()", frontend)
        self.assertIn("sequence: ++controller.sequence", frontend)
        self.assertIn("event.repeat", frontend)
        self.assertIn('addEventListener("keyup"', frontend)
        self.assertIn("isTextInput(event.target)", frontend)


if __name__ == "__main__":
    unittest.main()
