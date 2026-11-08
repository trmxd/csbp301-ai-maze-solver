"""SQLite-backed shared state for Class vs AI sessions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

from algorithms.astar import astar
from core.maze import Maze
from core.movement import validated_move


STATES = {"LOBBY", "STARTING", "PLAYING", "REVEAL", "ENDED"}
AVATARS = {"Explorer": "🧭", "Robot": "🤖", "Wizard": "🧙", "Astronaut": "🧑‍🚀"}
DIRECTIONS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


class _ClosingConnection(sqlite3.Connection):
    """Make ``with`` commit/rollback and then release the SQLite handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class ArenaError(ValueError):
    """A safe, user-facing arena validation error."""


@dataclass(frozen=True)
class Game:
    game_id: str
    state: str
    maze: Maze
    created_at: float
    started_at: float | None
    revealed_at: float | None
    ended_at: float | None
    ai_path: list[tuple[int, int]]
    ai_time: float = 0.0

    @property
    def ai_path_length(self) -> int | None:
        return len(self.ai_path) - 1 if self.ai_path else None


@dataclass(frozen=True)
class Player:
    token: str
    game_id: str
    nickname: str
    character: str
    joined_at: float
    start_time: float | None
    finish_time: float | None
    moves: int
    completed: bool
    position: tuple[int, int]
    path: list[tuple[int, int]]

    @property
    def elapsed(self) -> float | None:
        if self.start_time is None:
            return None
        end = self.finish_time if self.finish_time is not None else time.time()
        return max(0.0, end - self.start_time)


def _maze_json(maze: Maze) -> str:
    return json.dumps({
        "rows": maze.rows, "cols": maze.cols, "start": maze.start,
        "goal": maze.goal, "walls": sorted(maze.walls),
    }, separators=(",", ":"))


def _maze_from_json(value: str) -> Maze:
    data = json.loads(value)
    # Classroom rounds are intentionally unit-cost.  Ignore legacy terrain
    # fields so old database rows also load as ordinary mazes.
    return Maze(
        data["rows"], data["cols"], tuple(data["start"]),
        tuple(data["goal"]), {tuple(c) for c in data["walls"]},
    )


def _unit_cost_copy(maze: Maze) -> Maze:
    """Freeze only the grid geometry required by a classroom round."""

    return Maze(maze.rows, maze.cols, maze.start, maze.goal, set(maze.walls))


class ArenaStore:
    """Concurrency-safe arena operations shared by independent web sessions."""

    def __init__(self, path: str | Path | None = None):
        default = os.getenv("ARENA_DB_PATH", "/tmp/csbp301_arena.db")
        self.path = str(path or default)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10,
            isolation_level=None,
            factory=_ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS games (
                    game_id TEXT PRIMARY KEY, state TEXT NOT NULL, maze_json TEXT NOT NULL,
                    created_at REAL NOT NULL, started_at REAL, revealed_at REAL, ended_at REAL,
                    ai_path_json TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS players (
                    token TEXT PRIMARY KEY, game_id TEXT NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                    nickname TEXT NOT NULL COLLATE NOCASE, character TEXT NOT NULL,
                    joined_at REAL NOT NULL, start_time REAL, finish_time REAL,
                    moves INTEGER NOT NULL DEFAULT 0, completed INTEGER NOT NULL DEFAULT 0,
                    row INTEGER NOT NULL, col INTEGER NOT NULL, path_json TEXT NOT NULL,
                    UNIQUE(game_id, nickname)
                );
            """)
            if "ai_time" not in {row[1] for row in db.execute("PRAGMA table_info(games)")}:
                db.execute("ALTER TABLE games ADD COLUMN ai_time REAL NOT NULL DEFAULT 0")

    def create_game(self, maze: Maze, *, game_id: str | None = None, now: float | None = None) -> Game:
        game_id = (game_id or secrets.token_hex(3)).upper()
        timestamp = time.time() if now is None else now
        with self._connect() as db:
            db.execute(
                "INSERT INTO games(game_id,state,maze_json,created_at) VALUES(?,?,?,?)",
                (game_id, "LOBBY", _maze_json(_unit_cost_copy(maze)), timestamp),
            )
        return self.get_game(game_id)

    def get_game(self, game_id: str) -> Game:
        with self._connect() as db:
            row = db.execute("SELECT * FROM games WHERE game_id=?", (game_id.upper(),)).fetchone()
        if row is None:
            raise ArenaError("Game not found.")
        return Game(row["game_id"], row["state"], _maze_from_json(row["maze_json"]), row["created_at"], row["started_at"], row["revealed_at"], row["ended_at"], [tuple(c) for c in json.loads(row["ai_path_json"])], row["ai_time"])

    def join_game(self, game_id: str, nickname: str, character: str, *, now: float | None = None) -> Player:
        nickname = " ".join(nickname.strip().split())
        if not 1 <= len(nickname) <= 20:
            raise ArenaError("Nickname must contain 1–20 characters.")
        if character not in AVATARS:
            raise ArenaError("Choose a valid character.")
        game = self.get_game(game_id)
        token, timestamp = secrets.token_urlsafe(18), time.time() if now is None else now
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                state = db.execute(
                    "SELECT state FROM games WHERE game_id=?", (game.game_id,)
                ).fetchone()
                if state is None or state["state"] != "LOBBY":
                    raise ArenaError("This round has already started. Late joining is closed.")
                db.execute(
                    "INSERT INTO players(token,game_id,nickname,character,joined_at,row,col,path_json) VALUES(?,?,?,?,?,?,?,?)",
                    (token, game.game_id, nickname, character, timestamp, game.maze.start[0], game.maze.start[1], json.dumps([game.maze.start])),
                )
                db.commit()
        except sqlite3.IntegrityError as error:
            raise ArenaError("That nickname is already used in this game.") from error
        return self.get_player(game.game_id, token)

    def get_player(self, game_id: str, token: str) -> Player:
        with self._connect() as db:
            row = db.execute("SELECT * FROM players WHERE game_id=? AND token=?", (game_id.upper(), token)).fetchone()
        if row is None:
            raise ArenaError("Player not found in this game.")
        return Player(row["token"], row["game_id"], row["nickname"], row["character"], row["joined_at"], row["start_time"], row["finish_time"], row["moves"], bool(row["completed"]), (row["row"], row["col"]), [tuple(c) for c in json.loads(row["path_json"])])

    def players(self, game_id: str) -> list[Player]:
        with self._connect() as db:
            rows = db.execute("SELECT token FROM players WHERE game_id=? ORDER BY joined_at", (game_id.upper(),)).fetchall()
        return [self.get_player(game_id, row["token"]) for row in rows]

    def start_round(self, game_id: str, *, now: float | None = None) -> Game:
        timestamp = time.time() if now is None else now
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            game = db.execute("SELECT state FROM games WHERE game_id=?", (game_id.upper(),)).fetchone()
            count = db.execute("SELECT COUNT(*) FROM players WHERE game_id=?", (game_id.upper(),)).fetchone()[0]
            if game is None or game["state"] != "LOBBY":
                raise ArenaError("Only a lobby can be started.")
            if count == 0:
                raise ArenaError("At least one player must join before starting.")
            db.execute("UPDATE games SET state='STARTING',started_at=? WHERE game_id=?", (timestamp, game_id.upper()))
            db.execute("UPDATE players SET start_time=? WHERE game_id=?", (timestamp, game_id.upper()))
            db.execute("UPDATE games SET state='PLAYING' WHERE game_id=?", (game_id.upper(),))
            db.commit()
        return self.get_game(game_id)

    def move_player(self, game_id: str, token: str, direction: str, *, now: float | None = None) -> Player:
        if direction not in DIRECTIONS:
            raise ArenaError("Invalid direction.")
        timestamp = time.time() if now is None else now
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            game_row = db.execute("SELECT * FROM games WHERE game_id=?", (game_id.upper(),)).fetchone()
            row = db.execute("SELECT * FROM players WHERE game_id=? AND token=?", (game_id.upper(), token)).fetchone()
            if game_row is None or row is None:
                raise ArenaError("Game or player not found.")
            if game_row["state"] != "PLAYING":
                raise ArenaError("Movement is allowed only while the round is playing.")
            if row["completed"]:
                db.rollback()
                return self.get_player(game_id, token)
            maze = _maze_from_json(game_row["maze_json"])
            target = validated_move(maze, (row["row"], row["col"]), DIRECTIONS[direction])
            if target is None:
                db.rollback()
                return self.get_player(game_id, token)
            path = json.loads(row["path_json"])
            path.append(target)
            completed = target == maze.goal
            db.execute(
                "UPDATE players SET row=?,col=?,moves=moves+1,path_json=?,completed=?,finish_time=? WHERE token=?",
                (target[0], target[1], json.dumps(path), int(completed), timestamp if completed else None, token),
            )
            db.commit()
        return self.get_player(game_id, token)

    def reveal(self, game_id: str, *, now: float | None = None) -> Game:
        game = self.get_game(game_id)
        if game.state != "PLAYING":
            raise ArenaError("Results can be revealed only during an active round.")
        result = astar(game.maze.copy())
        timestamp = time.time() if now is None else now
        with self._connect() as db:
            db.execute("UPDATE games SET state='REVEAL',revealed_at=?,ai_path_json=? WHERE game_id=?", (timestamp, json.dumps(result.path), game.game_id))
            db.execute("UPDATE games SET ai_time=? WHERE game_id=?", (result.execution_time, game.game_id))
        return self.get_game(game_id)

    def end(self, game_id: str, *, now: float | None = None) -> Game:
        game = self.get_game(game_id)
        if game.state not in {"PLAYING", "REVEAL"}:
            raise ArenaError("Only a playing or revealed round can be ended.")
        with self._connect() as db:
            db.execute("UPDATE games SET state='ENDED',ended_at=? WHERE game_id=?", (time.time() if now is None else now, game.game_id))
        return self.get_game(game_id)

    def reset(self, game_id: str) -> Game:
        game = self.get_game(game_id)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM players WHERE game_id=?", (game.game_id,))
            db.execute("UPDATE games SET state='LOBBY',started_at=NULL,revealed_at=NULL,ended_at=NULL,ai_path_json='[]' WHERE game_id=?", (game.game_id,))
            db.commit()
        return self.get_game(game_id)

    def counts(self, game_id: str) -> dict[str, int]:
        players = self.players(game_id)
        finished = sum(player.completed for player in players)
        game = self.get_game(game_id)
        playing = len(players) - finished if game.state == "PLAYING" else 0
        return {"joined": len(players), "ready": len(players) if game.state == "LOBBY" else 0, "playing": playing, "finished": finished}

    def leaderboard(self, game_id: str) -> list[Player]:
        completed = [player for player in self.players(game_id) if player.completed]
        return sorted(completed, key=lambda player: (player.moves, player.elapsed or 0))

    def matched_ai(self, game_id: str) -> list[Player]:
        game = self.get_game(game_id)
        if game.state not in {"REVEAL", "ENDED"} or game.ai_path_length is None:
            return []
        return [player for player in self.leaderboard(game_id) if player.moves == game.ai_path_length]
