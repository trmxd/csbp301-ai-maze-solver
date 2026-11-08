"""Weighted search and shared-round regression tests."""
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from algorithms import ALGORITHMS
from arena.store import ArenaStore
from core.maze import Maze, random_maze, weighted_demo
from core.solver_utils import manhattan


class WeightedTests(unittest.TestCase):
    def test_human_movement_records_destination_energy(self):
        import app
        maze = Maze(2, 2, (0, 0), (0, 1), terrain={(0, 1): 'mud'}, weighted=True)
        state = SimpleNamespace(sim_maze=maze, human_active=True, human_path=[maze.start], human_started=0)
        with patch.object(app.st, 'session_state', state):
            app.move_human((0, 1))
        self.assertEqual(state.human_result['Path Length'], 1)
        self.assertEqual(state.human_result['Path Cost'], 5)

    def test_terrain_costs_and_start_is_free(self):
        maze = Maze(3, 3, terrain={(0, 0): "mud", (0, 1): "sand", (0, 2): "mud"}, weighted=True)
        self.assertEqual([maze.step_cost(c) for c in [(1, 0), (0, 1), (0, 2)]], [1, 3, 5])
        self.assertEqual(maze.path_energy([(0, 0), (0, 1), (0, 2)]), 8)
        maze.weighted = False
        self.assertEqual(maze.path_energy([(0, 0), (0, 1), (0, 2)]), 2)

    def test_demo_real_results(self):
        maze = weighted_demo()
        results = {name: solve(maze) for name, solve in ALGORITHMS.items()}
        self.assertEqual((results['BFS'].path_length, results['BFS'].path_cost), (4, 16))
        for name in ('A*', 'UCS'):
            self.assertEqual((results[name].path_length, results[name].path_cost), (6, 6))
        for result in results.values():
            self.assertTrue(result.solved)
            self.assertEqual(result.path_cost, maze.path_energy(result.path))
        self.assertEqual(results['A*'].scores[maze.goal][0], 6)

    def test_admissible_heuristic_at_every_demo_cell(self):
        maze = weighted_demo()
        for r in range(maze.rows):
            for c in range(maze.cols):
                test = maze.copy()
                test.start = (r, c)
                self.assertLessEqual(manhattan(test.start, test.goal), ALGORITHMS['UCS'](test).path_cost)

    def test_edit_copy_and_generation(self):
        maze = random_maze(8, 8, seed=42, weighted=True)
        self.assertTrue(maze.terrain)
        self.assertTrue(maze.is_open(maze.start) and maze.is_open(maze.goal))
        self.assertFalse(set(maze.terrain) & maze.walls)
        maze.set_terrain(maze.start, 'sand')
        self.assertEqual(maze.copy().terrain, maze.terrain)
        maze.walls.add((0, 1))
        with self.assertRaises(ValueError):
            maze.set_terrain((0, 1), 'mud')

    def test_shared_weighted_round_ranks_energy_and_matches_ai(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ArenaStore(Path(directory) / 'arena.db')
            game = store.create_game(weighted_demo())
            short = store.join_game(game.game_id, 'Short', 'Robot')
            cheap = store.join_game(game.game_id, 'Cheap', 'Wizard')
            store.start_round(game.game_id, now=10)
            for d in ['right'] * 4:
                store.move_player(game.game_id, short.token, d, now=12)
            for d in ['up'] + ['right'] * 4 + ['down']:
                store.move_player(game.game_id, cheap.token, d, now=15)
            store.reveal(game.game_id)
            self.assertEqual([p.nickname for p in store.leaderboard(game.game_id)], ['Cheap', 'Short'])
            self.assertEqual([p.nickname for p in store.matched_ai(game.game_id)], ['Cheap'])
            self.assertEqual(store.get_game(game.game_id).maze.terrain, weighted_demo().terrain)
