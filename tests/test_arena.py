"""Shared-state tests for Class vs AI — Live Maze Arena."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from arena.store import ArenaError, ArenaStore
from arena.ui import join_url, qr_image
from core.maze import Maze


class ArenaStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = ArenaStore(Path(self.temporary.name) / "arena.db")
        self.maze = Maze(3, 3, (0, 0), (0, 2), {(1, 1)})
        self.game = self.store.create_game(self.maze, game_id="ABC123", now=10)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def join(self, nickname="Ada", character="Explorer", now=11):
        return self.store.join_game(self.game.game_id, nickname, character, now=now)

    def test_create_game_preserves_one_shared_maze_copy(self):
        self.maze.walls.add((2, 2))
        stored = self.store.get_game("abc123")
        self.assertEqual(stored.state, "LOBBY")
        self.assertEqual(stored.maze.walls, {(1, 1)})

    def test_join_game_records_identity_and_start_position(self):
        player = self.join(character="Robot")
        self.assertEqual((player.nickname, player.character), ("Ada", "Robot"))
        self.assertEqual(player.position, self.maze.start)
        self.assertEqual(player.path, [self.maze.start])

    def test_duplicate_nickname_is_rejected_case_insensitively(self):
        self.join("Ada")
        with self.assertRaisesRegex(ArenaError, "already used"):
            self.join("ada", now=12)

    def test_multiple_players_join_the_same_game(self):
        self.join("Ada")
        self.join("Grace", "Wizard", 12)
        self.assertEqual([p.nickname for p in self.store.players("ABC123")], ["Ada", "Grace"])

    def test_nickname_and_character_validation(self):
        for nickname in ("", "x" * 21):
            with self.assertRaises(ArenaError):
                self.join(nickname)
        with self.assertRaisesRegex(ArenaError, "valid character"):
            self.join("Ada", "Dragon")

    def test_start_requires_a_player_and_sets_server_start_time(self):
        with self.assertRaisesRegex(ArenaError, "At least one"):
            self.store.start_round("ABC123", now=20)
        player = self.join()
        game = self.store.start_round("ABC123", now=20)
        self.assertEqual(game.state, "PLAYING")
        self.assertEqual(self.store.get_player(game.game_id, player.token).start_time, 20)

    def test_valid_movement_and_move_counting(self):
        player = self.join()
        self.store.start_round("ABC123", now=20)
        moved = self.store.move_player("ABC123", player.token, "right", now=21)
        self.assertEqual(moved.position, (0, 1))
        self.assertEqual(moved.moves, 1)
        self.assertEqual(moved.path, [(0, 0), (0, 1)])

    def test_walls_and_boundaries_do_not_count_as_moves(self):
        player = self.join()
        self.store.start_round("ABC123", now=20)
        for direction in ("up", "left"):
            player = self.store.move_player("ABC123", player.token, direction, now=21)
        player = self.store.move_player("ABC123", player.token, "down", now=22)
        player = self.store.move_player("ABC123", player.token, "right", now=23)
        self.assertEqual(player.position, (1, 0))
        self.assertEqual(player.moves, 1)

    def test_invalid_direction_and_movement_outside_play_are_rejected(self):
        player = self.join()
        with self.assertRaises(ArenaError):
            self.store.move_player("ABC123", player.token, "diagonal")
        with self.assertRaisesRegex(ArenaError, "only while"):
            self.store.move_player("ABC123", player.token, "right")

    def test_finish_and_elapsed_time_are_server_recorded_once(self):
        player = self.join()
        self.store.start_round("ABC123", now=20)
        self.store.move_player("ABC123", player.token, "right", now=22)
        finished = self.store.move_player("ABC123", player.token, "right", now=25.5)
        self.assertTrue(finished.completed)
        self.assertEqual(finished.moves, 2)
        self.assertEqual(finished.finish_time, 25.5)
        self.assertAlmostEqual(finished.elapsed, 5.5)
        repeated = self.store.move_player("ABC123", player.token, "left", now=30)
        self.assertEqual((repeated.moves, repeated.finish_time), (2, 25.5))

    def test_leaderboard_sorts_moves_then_elapsed_time(self):
        ada = self.join("Ada", now=11)
        grace = self.join("Grace", "Wizard", 12)
        linus = self.join("Linus", "Robot", 13)
        self.store.start_round("ABC123", now=20)
        for token, finish in ((ada.token, 26), (grace.token, 24)):
            self.store.move_player("ABC123", token, "right", now=21)
            self.store.move_player("ABC123", token, "right", now=finish)
        for direction in ("down", "down", "right", "right", "up", "up"):
            linus = self.store.move_player("ABC123", linus.token, direction, now=25)
        self.assertEqual([p.nickname for p in self.store.leaderboard("ABC123")], ["Grace", "Ada", "Linus"])
        self.assertEqual([p.moves for p in self.store.leaderboard("ABC123")], [2, 2, 6])

    def test_reveal_uses_astar_and_detects_optimal_matches(self):
        ada = self.join("Ada")
        grace = self.join("Grace", "Wizard", 12)
        self.store.start_round("ABC123", now=20)
        for token in (ada.token, grace.token):
            self.store.move_player("ABC123", token, "right", now=21)
            self.store.move_player("ABC123", token, "right", now=22)
        revealed = self.store.reveal("ABC123", now=30)
        self.assertEqual(revealed.state, "REVEAL")
        self.assertEqual(revealed.ai_path_length, 2)
        self.assertEqual([p.nickname for p in self.store.matched_ai("ABC123")], ["Ada", "Grace"])

    def test_late_join_is_rejected(self):
        self.join()
        self.store.start_round("ABC123", now=20)
        with self.assertRaisesRegex(ArenaError, "Late joining"):
            self.join("Grace", now=21)

    def test_end_round_preserves_unfinished_player_status(self):
        player = self.join()
        self.store.start_round("ABC123", now=20)
        ended = self.store.end("ABC123", now=30)
        player = self.store.get_player("ABC123", player.token)
        self.assertEqual(ended.state, "ENDED")
        self.assertFalse(player.completed)
        self.assertEqual(player.moves, 0)

    def test_reset_returns_to_empty_lobby(self):
        self.join()
        self.store.start_round("ABC123", now=20)
        self.store.reveal("ABC123", now=30)
        reset = self.store.reset("ABC123")
        self.assertEqual(reset.state, "LOBBY")
        self.assertEqual(reset.ai_path, [])
        self.assertEqual(self.store.players("ABC123"), [])

    def test_invalid_state_transitions_are_rejected(self):
        self.join()
        with self.assertRaises(ArenaError):
            self.store.reveal("ABC123")
        self.store.start_round("ABC123", now=20)
        with self.assertRaises(ArenaError):
            self.store.start_round("ABC123", now=21)
        self.store.reveal("ABC123", now=22)
        self.store.end("ABC123", now=23)
        with self.assertRaises(ArenaError):
            self.store.end("ABC123", now=24)

    def test_counts_hide_live_leaderboard_details(self):
        ada = self.join("Ada")
        self.join("Grace", "Wizard", 12)
        self.assertEqual(self.store.counts("ABC123"), {"joined": 2, "ready": 2, "playing": 0, "finished": 0})
        self.store.start_round("ABC123", now=20)
        self.store.move_player("ABC123", ada.token, "right", now=21)
        self.store.move_player("ABC123", ada.token, "right", now=22)
        self.assertEqual(self.store.counts("ABC123"), {"joined": 2, "ready": 0, "playing": 1, "finished": 1})

    def test_join_url_and_qr_are_session_specific(self):
        url = join_url("https://example.test/app", "ABC123")
        self.assertEqual(url, "https://example.test/app?arena=ABC123")
        image = qr_image(url)
        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(image), 100)
        with self.assertRaises(ArenaError):
            join_url("example.test/app", "ABC123")


if __name__ == "__main__":
    unittest.main()
