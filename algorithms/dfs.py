"""Depth-first search using a LIFO stack."""

from time import perf_counter

from core.maze import Coord, Maze
from core.solver_utils import SearchResult, build_result, neighbors


def dfs(maze: Maze) -> SearchResult:
    started = perf_counter()
    frontier = [maze.start]
    parents: dict[Coord, Coord | None] = {maze.start: None}
    explored: list[Coord] = []

    while frontier:
        current = frontier.pop()
        explored.append(current)
        if current == maze.goal:
            break
        # Reverse insertion preserves the documented up/right/down/left expansion order.
        for neighbor in reversed(neighbors(maze, current)):
            if neighbor not in parents:
                parents[neighbor] = current
                frontier.append(neighbor)

    return build_result("DFS", maze, parents, explored, set(parents), started)

