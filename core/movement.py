"""Movement rule shared by Human mode and the live classroom arena."""

from __future__ import annotations

from core.maze import Coord, Maze


def validated_move(maze: Maze, position: Coord, direction: Coord) -> Coord | None:
    """Return the legal destination, or ``None`` for a wall/boundary move."""

    target = (position[0] + direction[0], position[1] + direction[1])
    return target if maze.is_open(target) else None
