"""Maze representation, example mazes, and random maze generation."""

from __future__ import annotations

from dataclasses import dataclass, field
import random

Coord = tuple[int, int]


@dataclass
class Maze:
    """A rectangular four-directional grid maze."""

    rows: int
    cols: int
    start: Coord = (0, 0)
    goal: Coord | None = None
    walls: set[Coord] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.goal is None:
            self.goal = (self.rows - 1, self.cols - 1)
        self.validate()

    def validate(self) -> None:
        if self.rows < 2 or self.cols < 2:
            raise ValueError("A maze must have at least 2 rows and 2 columns.")
        if not self.in_bounds(self.start) or not self.in_bounds(self.goal):
            raise ValueError("Start and goal must be inside the grid.")
        self.walls = {cell for cell in self.walls if self.in_bounds(cell)}
        self.walls.discard(self.start)
        self.walls.discard(self.goal)

    def in_bounds(self, cell: Coord) -> bool:
        row, col = cell
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_open(self, cell: Coord) -> bool:
        return self.in_bounds(cell) and cell not in self.walls

    def copy(self) -> "Maze":
        return Maze(self.rows, self.cols, self.start, self.goal, set(self.walls))


def random_maze(
    rows: int,
    cols: int,
    density: float = 0.25,
    solvable: bool = True,
    seed: int | None = None,
) -> Maze:
    """Create a random maze; optionally preserve a guaranteed random path."""

    rng = random.Random(seed)
    start, goal = (0, 0), (rows - 1, cols - 1)
    protected: set[Coord] = {start, goal}

    if solvable:
        # Carve a monotonic but randomly ordered route from start to goal.
        cell = start
        protected.add(cell)
        while cell != goal:
            row, col = cell
            choices: list[Coord] = []
            if row < rows - 1:
                choices.append((row + 1, col))
            if col < cols - 1:
                choices.append((row, col + 1))
            cell = rng.choice(choices)
            protected.add(cell)

    walls = {
        (row, col)
        for row in range(rows)
        for col in range(cols)
        if (row, col) not in protected and rng.random() < density
    }
    return Maze(rows, cols, start, goal, walls)


def example_maze(name: str) -> Maze:
    """Return one of the two deterministic demonstration mazes."""

    if name == "Example 1 — Clear path":
        walls = {
            (1, 1), (1, 2), (1, 3), (1, 4),
            (3, 1), (3, 2), (3, 3), (3, 4),
            (5, 2), (5, 3), (5, 4), (5, 5),
        }
        return Maze(8, 8, (0, 0), (7, 7), walls)

    if name == "Example 2 — Multiple routes":
        walls = {
            (0, 3), (1, 1), (1, 3), (1, 5), (1, 6),
            (2, 1), (2, 5), (3, 1), (3, 2), (3, 3), (3, 5),
            (4, 3), (4, 5), (5, 1), (5, 2), (5, 3), (5, 5), (5, 6),
            (6, 1), (7, 3), (7, 4), (7, 5),
        }
        return Maze(9, 9, (0, 0), (8, 8), walls)

    raise ValueError(f"Unknown example maze: {name}")

