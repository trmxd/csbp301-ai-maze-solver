"""Uniform-cost search: choose the frontier node with minimum g(n)."""

import heapq
from itertools import count
from time import perf_counter

from core.maze import Coord, Maze
from core.solver_utils import SearchResult, build_result, neighbors


def ucs(maze: Maze) -> SearchResult:
    started = perf_counter()
    tie = count()
    frontier: list[tuple[int, int, Coord]] = [(0, next(tie), maze.start)]
    parents: dict[Coord, Coord | None] = {maze.start: None}
    costs: dict[Coord, int] = {maze.start: 0}
    explored: list[Coord] = []
    closed: set[Coord] = set()

    while frontier:
        current_cost, _, current = heapq.heappop(frontier)
        if current in closed:
            continue
        closed.add(current)
        explored.append(current)
        if current == maze.goal:
            break
        for neighbor in neighbors(maze, current):
            new_cost = current_cost + 1
            if new_cost < costs.get(neighbor, float("inf")):
                costs[neighbor] = new_cost
                parents[neighbor] = current
                heapq.heappush(frontier, (new_cost, next(tie), neighbor))

    return build_result("UCS", maze, parents, explored, set(costs), started)

