# CSBP301 AI Maze Solver & Human-vs-AI Simulator

An educational Search & Path Planning project built in Python and Streamlit. It demonstrates how A*, BFS, DFS, Uniform-Cost Search, and Greedy Best-First Search explore the same four-directional grid maze, then compares their measured behavior with a human attempt.

## 1. Project objective

The objective is to make classical artificial-intelligence search visible and measurable. A user builds or generates a maze, selects a search strategy, watches its explored nodes and final path, and compares the result with other algorithms or a manual attempt.

## 2. Problem definition

The environment is a rectangular grid. Some cells are blocked by walls. An agent must move from one Start cell to one Goal cell without crossing walls. Each legal move has cost 1.

## 3. State representation

A state is a `(row, column)` tuple. The maze stores its row/column dimensions, Start, Goal, and a set of wall coordinates.

## 4. Actions

The legal actions are Up, Right, Down, and Left. Diagonal movement is not allowed. An action is legal only when its destination is inside the grid and is not a wall.

## 5. Goal

The goal test is `current_cell == goal_cell`. Each algorithm keeps a parent pointer for every discovered cell so a completed path can be reconstructed backwards from Goal to Start.

## 6. Algorithms

- **A\*** uses a priority queue ordered by `f(n) = g(n) + h(n)`.
- **BFS** uses a FIFO queue and expands the shallowest nodes first.
- **DFS** uses a LIFO stack and expands the deepest available branch first.
- **UCS** uses a priority queue ordered by accumulated path cost `g(n)`.
- **Greedy Best-First Search** uses a priority queue ordered only by `h(n)`.

All algorithms are implemented from scratch with Python's `deque`, list, and `heapq`; no pathfinding library is used. Neighbor ordering is deterministic: Up, Right, Down, Left.

## 7. How A* works

A* evaluates each frontier node with:

```text
g(n) = exact cost from Start to n
h(n) = estimated cost from n to Goal
f(n) = g(n) + h(n)
```

It repeatedly expands the frontier node with the lowest `f`. If a cheaper route to a cell is found, its cost and parent are updated. With unit movement costs and the Manhattan heuristic, A* returns a lowest-cost path.

## 8. Why Manhattan distance is used

Manhattan distance is `abs(row1-row2) + abs(col1-col2)`. It matches a grid where only horizontal and vertical moves are allowed. It never overestimates the remaining cost in this unit-cost setting, which makes it an admissible heuristic for A*.

## 9. Human vs AI simulation

Click **Start Human Attempt** to freeze a copy of the current maze. Move with the four on-screen arrow buttons. The application records the path, move count, distinct visited cells, and elapsed time. **Run AI Simulation** runs all five algorithms on that same frozen maze and animates each result before displaying one comparison table.

## 10. Evaluation metrics

- **Solved:** whether Goal was reached.
- **Path length / cost:** number of moves; cost equals length because every move costs 1.
- **Expanded nodes:** nodes removed from the frontier and processed.
- **Visited nodes:** distinct nodes discovered.
- **Time:** measured algorithm execution time using `time.perf_counter` (animation time is excluded).

## 11. How to run

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The sidebar selects Start and Goal, loads either predefined example, creates a random maze, clears walls, selects an algorithm, adjusts animation speed, and optionally displays A* scores. In the wall editor, tick a cell to make it a wall. Start defaults to the upper-left cell and Goal defaults to the lower-right cell.

The maze is deliberately rendered at a compact fixed size so the controls, results, and comparison table remain visible on ordinary laptop screens.

## 12. Testing

The tests use the Python standard-library `unittest` runner:

```bash
python -m unittest discover -s tests -v
```

They cover Start equals Goal, a straight path, obstacles, no path, multiple routes, generated solvable mazes, A* optimality, all five algorithms, parent reconstruction, and path validity.

## 13. Limitations

- All moves have cost 1; terrain with different costs is not included.
- The grid is limited to 20×20 to keep animations readable and lightweight.
- Streamlit animations run synchronously, so there is Play/Replay and Reset but no mid-animation Pause.
- Manual movement uses on-screen controls rather than global keyboard capture, avoiding an extra component dependency.
- Algorithm timings on very small mazes can vary between runs because they are below one millisecond.

## 14. Future improvements

Possible extensions include weighted terrain, diagonal movement with a matching heuristic, maze import/export, bidirectional search, and a richer non-blocking animation controller. They are intentionally excluded from this minimal course project.
