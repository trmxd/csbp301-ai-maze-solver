"""Breadth-first search using a FIFO queue."""

from collections import deque
from time import perf_counter

from core.maze import Coord, Maze
from core.solver_utils import SearchResult, build_result, neighbors


def bfs(maze: Maze) -> SearchResult:
    started = perf_counter()
    frontier = deque([maze.start])
    parents: dict[Coord, Coord | None] = {maze.start: None}
    explored: list[Coord] = []

    while frontier:
        current = frontier.popleft()
        explored.append(current)
        if current == maze.goal:
            break
        for neighbor in neighbors(maze, current):
            if neighbor not in parents:
                parents[neighbor] = current
                frontier.append(neighbor)

    return build_result("BFS", maze, parents, explored, set(parents), started)

