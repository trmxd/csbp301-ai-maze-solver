"""Search algorithms exposed through one small registry."""

from algorithms.astar import astar
from algorithms.bfs import bfs
from algorithms.dfs import dfs
from algorithms.greedy import greedy
from algorithms.ucs import ucs

ALGORITHMS = {
    "A*": astar,
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "Greedy": greedy,
}

