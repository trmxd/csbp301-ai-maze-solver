"""Correctness tests for every search implementation."""

import unittest

from algorithms import ALGORITHMS
from algorithms.astar import astar
from algorithms.bfs import bfs
from algorithms.dfs import dfs
from algorithms.greedy import greedy
from algorithms.ucs import ucs
from core.maze import Maze, random_maze
from core.solver_utils import reconstruct_path


def assert_valid_path(test: unittest.TestCase, maze: Maze, path: list[tuple[int, int]]) -> None:
    test.assertTrue(path)
    test.assertEqual(path[0], maze.start)
    test.assertEqual(path[-1], maze.goal)
    for cell in path:
        test.assertNotIn(cell, maze.walls)
        test.assertTrue(maze.in_bounds(cell))
    for first, second in zip(path, path[1:]):
        test.assertEqual(abs(first[0] - second[0]) + abs(first[1] - second[1]), 1)


class SearchAlgorithmTests(unittest.TestCase):
    def test_start_equals_goal(self) -> None:
        maze = Maze(3, 3, (1, 1), (1, 1))
        for solve in ALGORITHMS.values():
            result = solve(maze)
            self.assertTrue(result.solved)
            self.assertEqual(result.path, [(1, 1)])
            self.assertEqual(result.path_cost, 0)

    def test_simple_straight_path(self) -> None:
        maze = Maze(2, 5, (0, 0), (0, 4), {(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)})
        for solve in ALGORITHMS.values():
            result = solve(maze)
            self.assertTrue(result.solved)
            self.assertEqual(result.path_length, 4)

    def test_maze_with_obstacles(self) -> None:
        maze = Maze(5, 5, walls={(0, 1), (1, 1), (2, 1), (3, 1)})
        for solve in ALGORITHMS.values():
            result = solve(maze)
            self.assertTrue(result.solved)
            assert_valid_path(self, maze, result.path)

    def test_no_possible_path(self) -> None:
        maze = Maze(3, 3, walls={(0, 1), (1, 0)})
        for solve in ALGORITHMS.values():
            result = solve(maze)
            self.assertFalse(result.solved)
            self.assertEqual(result.path, [])

    def test_multiple_possible_paths(self) -> None:
        maze = Maze(5, 5, walls={(1, 2), (2, 2), (3, 2)})
        for solve in ALGORITHMS.values():
            assert_valid_path(self, maze, solve(maze).path)

    def test_random_solvable_maze(self) -> None:
        for seed in range(10):
            maze = random_maze(10, 10, density=0.4, solvable=True, seed=seed)
            self.assertTrue(astar(maze).solved)

    def test_astar_returns_lowest_cost_path(self) -> None:
        maze = Maze(7, 7, walls={(1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (4, 3)})
        self.assertEqual(astar(maze).path_cost, bfs(maze).path_cost)

    def test_bfs(self) -> None:
        result = bfs(Maze(4, 4))
        self.assertEqual(result.path_length, 6)

    def test_dfs(self) -> None:
        maze = Maze(4, 4, walls={(1, 1)})
        result = dfs(maze)
        self.assertTrue(result.solved)
        assert_valid_path(self, maze, result.path)

    def test_ucs(self) -> None:
        maze = Maze(6, 6, walls={(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)})
        self.assertEqual(ucs(maze).path_cost, bfs(maze).path_cost)

    def test_greedy(self) -> None:
        maze = Maze(5, 5, walls={(0, 1), (1, 1), (2, 1)})
        result = greedy(maze)
        self.assertTrue(result.solved)
        assert_valid_path(self, maze, result.path)

    def test_parent_reconstruction(self) -> None:
        parents = {(0, 0): None, (0, 1): (0, 0), (1, 1): (0, 1)}
        self.assertEqual(reconstruct_path(parents, (1, 1)), [(0, 0), (0, 1), (1, 1)])
        self.assertEqual(reconstruct_path(parents, (2, 2)), [])

    def test_all_paths_start_end_and_avoid_walls(self) -> None:
        maze = Maze(8, 8, walls={(1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (5, 5)})
        for solve in ALGORITHMS.values():
            assert_valid_path(self, maze, solve(maze).path)


if __name__ == "__main__":
    unittest.main()

