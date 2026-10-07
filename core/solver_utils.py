"""Shared types and small utilities used by all search algorithms."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from core.maze import Coord, Maze


@dataclass
class SearchResult:
    algorithm: str
    solved: bool
    path: list[Coord]
    explored_order: list[Coord]
    expanded_nodes: int
    visited_nodes: int
    execution_time: float
    scores: dict[Coord, tuple[float, float, float]] = field(default_factory=dict)

    @property
    def path_length(self) -> int | None:
        return len(self.path) - 1 if self.solved else None

    @property
    def path_cost(self) -> int | None:
        # Every move has unit cost in this project.
        return self.path_length


def manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors(maze: Maze, cell: Coord) -> list[Coord]:
    """Return valid neighbors in a deterministic order: up, right, down, left."""

    row, col = cell
    candidates = [(row - 1, col), (row, col + 1), (row + 1, col), (row, col - 1)]
    return [candidate for candidate in candidates if maze.is_open(candidate)]


def reconstruct_path(parents: dict[Coord, Coord | None], goal: Coord) -> list[Coord]:
    if goal not in parents:
        return []
    path: list[Coord] = []
    current: Coord | None = goal
    while current is not None:
        path.append(current)
        current = parents[current]
    path.reverse()
    return path


def build_result(
    name: str,
    maze: Maze,
    parents: dict[Coord, Coord | None],
    explored: list[Coord],
    discovered: set[Coord],
    started_at: float,
    scores: dict[Coord, tuple[float, float, float]] | None = None,
) -> SearchResult:
    solved = maze.goal in parents
    return SearchResult(
        algorithm=name,
        solved=solved,
        path=reconstruct_path(parents, maze.goal) if solved else [],
        explored_order=explored,
        expanded_nodes=len(explored),
        visited_nodes=len(discovered),
        execution_time=perf_counter() - started_at,
        scores=scores or {},
    )

