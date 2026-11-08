"""Tests for the non-blocking browser animation payload."""

import unittest
from types import SimpleNamespace

import matplotlib.pyplot as plt

from algorithms.astar import astar
from core.maze import Maze
from ui.browser_animation import _animation_data
from ui.visualization import maze_figure


class BrowserAnimationTests(unittest.TestCase):
    def test_visualization_accepts_legacy_unit_cost_maze(self):
        legacy_maze = SimpleNamespace(
            rows=2, cols=2, start=(0, 0), goal=(1, 1), walls=set()
        )
        figure = maze_figure(legacy_maze)
        self.assertIsNotNone(figure)
        plt.close(figure)

    def test_payload_preserves_search_steps_and_maze(self) -> None:
        maze = Maze(3, 3, (0, 0), (2, 2), {(1, 1)})
        result = astar(maze)

        data = _animation_data(maze, [result], speed=0.06, show_scores=True)

        self.assertEqual(data["rows"], 3)
        self.assertEqual(data["cols"], 3)
        self.assertEqual(data["walls"], [[1, 1]])
        self.assertEqual(data["delay"], 60)
        self.assertEqual(data["runs"][0]["path"], [list(cell) for cell in result.path])
        self.assertEqual(data["runs"][0]["explored"], [list(cell) for cell in result.explored_order])

    def test_fast_animation_uses_a_visible_frame_delay(self) -> None:
        maze = Maze(2, 2)
        result = astar(maze)

        data = _animation_data(maze, [result], speed=0.001, show_scores=False)

        self.assertEqual(data["delay"], 28)

    def test_instant_animation_has_no_delay(self) -> None:
        maze = Maze(2, 2)
        result = astar(maze)

        data = _animation_data(maze, [result], speed=0.0, show_scores=False)

        self.assertEqual(data["delay"], 0)


if __name__ == "__main__":
    unittest.main()
