"""A* search: choose the frontier node with minimum f(n) = g(n) + h(n)."""

from __future__ import annotations

import heapq
from itertools import count
from time import perf_counter

from core.maze import Coord, Maze
from core.solver_utils import SearchResult, build_result, manhattan, neighbors


def astar(maze: Maze) -> SearchResult:
    started = perf_counter()
    tie = count()
    h_start = manhattan(maze.start, maze.goal)
    frontier: list[tuple[int, int, Coord]] = [(h_start, next(tie), maze.start)]
    parents: dict[Coord, Coord | None] = {maze.start: None}
    g_cost: dict[Coord, int] = {maze.start: 0}
    scores: dict[Coord, tuple[float, float, float]] = {
        maze.start: (0, h_start, h_start)
    }
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
            tentative_g = g_cost[current] + 1
            if tentative_g < g_cost.get(neighbor, float("inf")):
                parents[neighbor] = current
                g_cost[neighbor] = tentative_g
                h_cost = manhattan(neighbor, maze.goal)
                f_cost = tentative_g + h_cost
                scores[neighbor] = (tentative_g, h_cost, f_cost)
                heapq.heappush(frontier, (f_cost, next(tie), neighbor))

    return build_result("A*", maze, parents, explored, set(g_cost), started, scores)

