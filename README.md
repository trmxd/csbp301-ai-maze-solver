# CSBP301 AI Maze Solver & Human-vs-AI Simulator

An educational Search & Path Planning project built in Python and Streamlit. It demonstrates how A*, BFS, DFS, Uniform-Cost Search, and Greedy Best-First Search explore the same four-directional grid maze, then compares their measured behavior with a human attempt.

**Group 5**

- Hiad Khaldoun Alrefai Alhariri — 700051118
- Mohammed Khalid Khamis Alnaqbi — 202302562

## Live web app

## Weighted Terrain / Energy-Aware Path Planning

Enable **Energy / Weighted Terrain** in the sidebar. The terrain editor below the wall editor assigns Normal (1), Sand (3), or Mud (5) to open cells. Walls take precedence; Start and Goal stay open. Random generation uses 60% normal, 25% sand, and 15% mud when weighted mode is enabled. Disabling it makes all moves cost 1 while preserving assigned terrain for later use.

Every move charges the destination cell, including entry into Goal. Start is initially free; returning to Start charges its terrain like any other move. UCS accumulates these costs. A* accumulates the same costs for g(n), with Manhattan distance × 1 for its admissible, consistent heuristic. BFS continues to minimize moves; DFS and Greedy retain their original search policies. All five report the actual energy of their resulting route separately from its move count.

Human energy is computed from the canonical server path. Weighted terrain remains available in the Solver and Human vs AI modes. Class vs AI deliberately converts the selected grid geometry to an ordinary unit-cost maze and ranks players by moves, then elapsed time.

### Reproducible presentation example

Click **Load energy tradeoff demo**. This creates a 5×5 open grid, Start (1,0), Goal (1,4), with mud at (1,1), (1,2), (1,3).

| Algorithm | Actual moves | Actual energy |
|---|---:|---:|
| BFS | 4 | 16 |
| UCS | 6 | 6 |
| A* | 6 | 6 |

Click **Compare all algorithms on this maze** to calculate the results. BFS crosses three mud cells; UCS/A* detour along normal cells. These values are reproduced by automated tests, not illustrative fabricated metrics. In a four-directional grid, paths between the same endpoints have the same move-count parity, so an 8-versus-11-move comparison cannot occur under this model.

### Report-ready technical note

Energy-aware planning extends the existing grid with a sparse cell-to-terrain mapping and an explicit weighted-mode flag. Destination costs are shared by all result calculations. Only UCS and A* priority calculations change; maze connectivity and other search policies remain intact. Tests verify terrain costs, free initial Start, real weighted path costs, BFS/UCS/A* tradeoffs, Manhattan admissibility at every demo cell, terrain editing/copying/generation, unit-cost classroom conversion, shared classroom persistence, move-based ranking, and AI matching. The current automated suite passes 55 tests. Browser rendering and physical phone behavior require device validation; automated tests do not establish network responsiveness under classroom load. No paid API or extra dependency is required. Existing SQLite deployment limitations still apply.

Open the project in your browser: **[CSBP301 AI Maze Solver](https://csbp301-ai-maze-solver.streamlit.app/)**

## Class vs AI — Live Maze Arena

The **🏆 Class vs AI** tab adds a real shared classroom round without replacing the existing solver or Human vs AI simulation.

### Host workflow

1. Open **🏆 Class vs AI** on the presentation laptop.
2. Open **Edit the Classroom Maze** to change walls, or use the sidebar to change size, Start, Goal, or generate a maze.
3. Click **Create New Class Game**. The app freezes one copy of the edited maze and generates a unique game ID. Editing is locked for that round so every student receives exactly the same maze.
4. Display the generated QR code and join URL. The **Join by Game Code** button is beside **Create New Class Game**. The dashboard updates the Joined, Ready, Playing, and Finished counts automatically and lists every player's live status.
5. Wait for students, then click **Start Round**. Joining closes as soon as play starts.
6. During play, the A* route and leaderboard remain hidden. The host sees only the shared maze, player names, status, and completion counters.
7. Click **End Round** to stop movement and reveal an animated Top 3 podium. Completed players are ranked by moves and then server-recorded elapsed time.
8. **Reveal AI** remains available as an optional comparison. It is not required for the classroom competition. Use **Reset Round** to clear players and return the same game to an empty lobby.

### Student workflow

1. Scan the QR code, open the session-specific link, or open the code-entry page and type the host's game code.
2. Enter a unique nickname of 1–20 characters and choose Explorer, Robot, Wizard, or Astronaut.
3. Wait for the host. A player cannot move in the lobby.
4. After the host starts, solve the same maze using the large phone-friendly touch arrows. Arrow Keys and WASD also work on devices with keyboards.
5. The server validates every request. Walls and boundaries do not move the player or increase the move count. Repeated finish requests do not alter a completed result.

The Class vs AI arena always freezes an ordinary unit-cost maze, even if weighted terrain is enabled in another app mode. Terrain and energy scoring are intentionally excluded from classroom rounds. The leaderboard contains completed players only. It sorts by the lowest valid move count and then the lowest server-recorded elapsed time. Unfinished players remain stored as unfinished and are never given a fabricated result. With unit-cost four-directional movement and the existing admissible Manhattan heuristic, A* is used as the shortest-path benchmark for this mode; the other algorithms remain available in the original solver.

### Multiplayer architecture

Streamlit `session_state` is isolated per browser, so the arena does not use it as the multiplayer source of truth. `arena/store.py` stores games, frozen maze JSON, players, server timestamps, ordered paths, and lifecycle state in a shared SQLite database. Short write transactions serialize joins, starts, and movements. Every phone addresses the same game by ID and receives the maze stored for that game. The host and player fragments poll the database at short intervals for live counters and state changes.

Player metrics are computed from server-owned records. Movement calls use the same `core/movement.py` validator as the existing Human mode. The AI reveal calls the existing `algorithms/astar.py`; no search implementation is duplicated.

The real join URL has this form:

```text
https://your-app.example/?arena=GAMEID
```

The QR code is generated dynamically from that exact URL. Configure deployments with:

```bash
export ARENA_BASE_URL="https://your-public-app.example/"
export ARENA_DB_PATH="/tmp/csbp301_arena.db"
streamlit run app.py
```

For local testing, set `ARENA_BASE_URL` to a URL other devices can reach, such as the computer's LAN address (`http://192.168.x.x:8501/`), not `localhost`. Start Streamlit with `streamlit run app.py --server.address 0.0.0.0`, keep all phones on the same network, open the Class vs AI tab on the host, and scan its QR code from two or more phones.

For a public classroom link, the Streamlit deployment itself must allow public/anonymous access. If the app is private, scanned phones are redirected to Streamlit sign-in before they can join; change the app visibility in Streamlit Community Cloud or have every participant sign in. This is a deployment access setting, not something the QR code can bypass.

SQLite is deliberately the smallest reliable architecture for this course demonstration and a single Streamlit server process. On Streamlit Community Cloud, local files are ephemeral: games disappear when the app container restarts. A scaled multi-replica deployment would need a shared external SQL database and a corresponding store adapter; no credentials or external service are required for the current single-instance demo.

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

Click **Start Human Attempt** to freeze a copy of the current maze. The Human attempt appears on the right and the AI simulation appears on the left for direct visual comparison. Move with the unchanged on-screen arrow buttons or use the keyboard Arrow Keys/WASD. Both inputs call the same validated movement function. The application records the path, move count, distinct visited cells, and elapsed time. **Run AI Simulation** runs all five algorithms on that same frozen maze and animates each result before displaying one comparison table.

Rapid keyboard presses are buffered briefly in the local browser component and sent as an ordered, numbered history. Python processes only unseen sequence numbers, so a newer Streamlit component value can recover presses coalesced during a rerun without duplicating movement. OS key-repeat is ignored until keyup; normal separate presses remain responsive.

The Human maze itself is rendered by that persistent local component. Keyboard moves are previewed immediately in the browser while the ordered history synchronizes with Streamlit, preventing the maze from disappearing during Python reruns. `move_human()` remains the canonical validator for walls, boundaries, path tracking, timing, and completion.

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

The search visualization runs in a lightweight browser-side grid, animating every expanded node and drawing the final route step by step without blocking Streamlit. It includes progress, pause/resume, skip, and replay controls. Lightweight CSS adds a polished entrance, hero panel, bordered simulation cards, metric cards, and button feedback without adding frontend dependencies.

## 12. Testing

The tests use the Python standard-library `unittest` runner:

```bash
python -m unittest discover -s tests -v
```

They cover Start equals Goal, a straight path, obstacles, no path, multiple routes, generated solvable mazes, A* optimality, all five algorithms, parent reconstruction, and path validity. Arena tests additionally cover game creation, shared-maze persistence, joins, nickname validation, state transitions, valid/invalid moves, server timing, finish idempotency, ranking and tie-breaking, A* reveal and matching, late joins, counters, reset/end behavior, and session-specific QR generation.

## 13. Limitations

- All moves have cost 1; terrain with different costs is not included.
- The grid is limited to 20×20 to keep animations readable and lightweight.
- Animation is visual only; pausing or skipping it does not change the already-computed algorithm result.
- Keyboard movement is captured by a tiny local browser component and is enabled only while the Human tab is visible and an attempt is active.
- Algorithm timings on very small mazes can vary between runs because they are below one millisecond.
- The included SQLite arena is shared across browser sessions in one Streamlit process, but it is not a multi-replica database. Streamlit Community Cloud may erase active games when the container restarts.
- Automatic public URL discovery is not reliable in every deployment, so the host screen uses `ARENA_BASE_URL` (or its editable URL field) to construct the real session link and QR code.
- A private Streamlit deployment requires each student to authenticate. Set the deployment to public for a scan-and-join classroom demo without sign-in.

## 14. Future improvements

Possible extensions include weighted terrain, diagonal movement with a matching heuristic, maze import/export, bidirectional search, and a richer non-blocking animation controller. They are intentionally excluded from this minimal course project.
