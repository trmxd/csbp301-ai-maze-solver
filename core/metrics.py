"""Helpers for presenting search metrics."""

from __future__ import annotations

from core.solver_utils import SearchResult


def result_row(result: SearchResult) -> dict[str, object]:
    return {
        "Method": result.algorithm,
        "Solved?": "Yes" if result.solved else "No",
        "Path Length": result.path_length if result.path_length is not None else "—",
        "Path Cost": result.path_cost if result.path_cost is not None else "—",
        "Expanded Nodes": result.expanded_nodes,
        "Visited Nodes": result.visited_nodes,
        "Time (ms)": round(result.execution_time * 1000, 3),
    }

