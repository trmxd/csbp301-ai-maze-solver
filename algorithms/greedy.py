"""Greedy best-first search: choose the node with minimum h(n)."""

import heapq
from itertools import count
from time import perf_counter

from core.maze import Coord, Maze
from core.solver_utils import SearchResult, build_result, manhattan, neighbors


def greedy(maze: Maze) -> SearchResult:
    started = perf_counter()
    tie = count()
    frontier: list[tuple[int, int, Coord]] = [
        (manhattan(maze.start, maze.goal), next(tie), maze.start)
    ]
    parents: dict[Coord, Coord | None] = {maze.start: None}
    explored: list[Coord] = []
    closed: set[Coord] = set()

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current in closed:
            continue
        closed.add(current)
        explored.append(current)
        if current == maze.goal:
            break
        for neighbor in neighbors(maze, current):
            if neighbor not in parents:
                parents[neighbor] = current
                heapq.heappush(
                    frontier,
                    (manhattan(neighbor, maze.goal), next(tie), neighbor),
                )

    return build_result("Greedy", maze, parents, explored, set(parents), started)

