"""Matplotlib rendering for the maze, search trace, and paths."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

from core.maze import Coord, Maze


COLORS = ["#f8fafc", "#bae6fd", "#facc15", "#1f2937", "#22c55e", "#ef4444", "#c084fc", "#fb923c"]
LABELS = {
    "Start": "#22c55e",
    "Goal": "#ef4444",
    "Wall": "#1f2937",
    "Visited": "#bae6fd",
    "Final path": "#facc15",
    "Human path": "#c084fc",
    "Current": "#fb923c",
}


def maze_figure(
    maze: Maze,
    explored: list[Coord] | None = None,
    path: list[Coord] | None = None,
    human_path: list[Coord] | None = None,
    current: Coord | None = None,
    active: Coord | None = None,
    scores: dict[Coord, tuple[float, float, float]] | None = None,
    show_scores: bool = False,
) -> plt.Figure:
    grid = np.zeros((maze.rows, maze.cols), dtype=int)
    for cell in explored or []:
        grid[cell] = 1
    for cell in path or []:
        grid[cell] = 2
    for cell in human_path or []:
        grid[cell] = 6
    for cell in maze.walls:
        grid[cell] = 3
    grid[maze.start] = 4
    grid[maze.goal] = 5
    if current is not None and current not in (maze.start, maze.goal):
        grid[current] = 7

    # Keep the maze presentation-friendly instead of filling the page width.
    size = max(3.6, min(5.0, max(maze.rows, maze.cols) * 0.34))
    fig, ax = plt.subplots(figsize=(size, size))
    ax.imshow(grid, cmap=ListedColormap(COLORS), vmin=0, vmax=len(COLORS) - 1)
    ax.set_xticks(np.arange(-0.5, maze.cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, maze.rows, 1), minor=True)
    ax.grid(which="minor", color="#94a3b8", linewidth=0.7)
    ax.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)

    if show_scores and scores and maze.rows <= 12 and maze.cols <= 12:
        for (row, col), (g, h, f) in scores.items():
            if (row, col) not in maze.walls:
                ax.text(col, row, f"g={g:g}\nh={h:g}\nf={f:g}", ha="center", va="center", fontsize=6, color="#0f172a")

    # Highlight the currently animated step without changing maze state.
    if active is not None:
        row, col = active
        ax.add_patch(
            plt.Circle(
                (col, row), 0.31, fill=False, color="#f97316",
                linewidth=3.0, alpha=0.95, zorder=5,
            )
        )

    # Connect revealed route cells so the final path reads clearly as motion.
    if path and len(path) > 1:
        ax.plot(
            [cell[1] for cell in path],
            [cell[0] for cell in path],
            color="#eab308", linewidth=2.2, alpha=0.9, zorder=4,
        )

    fig.tight_layout(pad=0.1)
    return fig
