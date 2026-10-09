"""Streamlit interface for the CSBP301 AI Maze Solver project."""

from __future__ import annotations

import time

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from algorithms import ALGORITHMS
from core.maze import Maze, example_maze, random_maze
from core.metrics import result_row
from ui.keyboard_component import direction_for_key, keyboard_event
from ui.visualization import LABELS, maze_figure


ALGORITHM_EXPLANATIONS = {
    "A*": "A* selects the smallest f(n) = g(n) + h(n). Here g is the path cost from Start and h is Manhattan distance to Goal.",
    "BFS": "Breadth-First Search uses a FIFO queue and explores level by level. With unit costs, it finds a shortest path.",
    "DFS": "Depth-First Search uses a LIFO stack and explores the deepest available branch first. Its path is not guaranteed shortest.",
    "UCS": "Uniform-Cost Search selects the lowest accumulated path cost g(n). It is optimal for non-negative costs.",
    "Greedy": "Greedy Best-First Search selects the lowest heuristic h(n). It is often fast, but is not guaranteed to find a shortest path.",
}


def apply_app_style() -> None:
    """Add lightweight visual polish without external dependencies."""

    st.markdown(
        """
        <style>
        @keyframes appEnter {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 0 rgba(56, 189, 248, 0); }
            50% { box-shadow: 0 0 24px rgba(56, 189, 248, .18); }
        }
        .stMainBlockContainer { animation: appEnter .45s ease-out; padding-top: 2rem; }
        .maze-hero {
            padding: 1.15rem 1.35rem; margin-bottom: 1rem; border-radius: 18px;
            border: 1px solid rgba(56, 189, 248, .25);
            background: linear-gradient(120deg, rgba(14,165,233,.12), rgba(99,102,241,.08));
            animation: glow 4s ease-in-out infinite;
        }
        .maze-hero h1 { margin: 0; font-size: clamp(1.75rem, 4vw, 2.65rem); }
        .maze-hero p { margin: .35rem 0 0; color: #64748b; }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(148,163,184,.25); border-radius: 14px;
            padding: .75rem 1rem; background: rgba(148,163,184,.06);
            transition: transform .18s ease, border-color .18s ease;
        }
        div[data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: #38bdf8; }
        div.stButton > button {
            border-radius: 10px; transition: transform .16s ease, box-shadow .16s ease;
        }
        div.stButton > button:hover {
            transform: translateY(-1px); box-shadow: 0 7px 18px rgba(15,23,42,.12);
        }
        div[data-testid="stImage"] img { border-radius: 14px; }
        div[data-testid="stTabs"] button[role="tab"] { font-weight: 650; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "maze": example_maze("Example 1 — Clear path"),
        "result": None,
        "comparison": None,
        "human_active": False,
        "human_path": [],
        "human_started": None,
        "human_result": None,
        "sim_maze": None,
        "sim_results": None,
        "editor_version": 0,
        "last_keyboard_event": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_run_state() -> None:
    st.session_state.result = None
    st.session_state.comparison = None
    st.session_state.human_active = False
    st.session_state.human_path = []
    st.session_state.human_result = None
    st.session_state.sim_maze = None
    st.session_state.sim_results = None
    st.session_state.last_keyboard_event = None


def replace_maze(maze: Maze) -> None:
    """Install a new maze and discard widget/run state tied to the old one."""

    st.session_state.maze = maze
    st.session_state.editor_version += 1
    clear_run_state()


def show_legend() -> None:
    items = " ".join(
        f'<span style="white-space:nowrap;margin-right:12px"><span style="display:inline-block;width:12px;height:12px;background:{color};border:1px solid #64748b;margin-right:4px"></span>{label}</span>'
        for label, color in LABELS.items()
    )
    st.markdown(items, unsafe_allow_html=True)


def show_maze(fig) -> None:
    """Render a compact maze without stretching it to the page width."""

    st.pyplot(fig, width="content")
    plt.close(fig)


def edit_maze(maze: Maze, key: str) -> None:
    st.caption("Tick cells to make walls. Start and Goal are always kept open.")
    wall_data = [
        [((row, col) in maze.walls) for col in range(maze.cols)]
        for row in range(maze.rows)
    ]
    frame = pd.DataFrame(wall_data, columns=[str(col) for col in range(maze.cols)])
    edited = st.data_editor(frame, key=key, hide_index=False, height=min(520, 38 + 35 * maze.rows))
    new_walls = {
        (row, col)
        for row in range(maze.rows)
        for col in range(maze.cols)
        if bool(edited.iloc[row, col])
    }
    new_walls.discard(maze.start)
    new_walls.discard(maze.goal)
    if new_walls != maze.walls:
        maze.walls = new_walls
        clear_run_state()


def display_result(result) -> None:
    cols = st.columns(5)
    cols[0].metric("Algorithm", result.algorithm)
    cols[1].metric("Solved", "Yes" if result.solved else "No")
    cols[2].metric("Path length", result.path_length if result.solved else "—")
    cols[3].metric("Path cost", result.path_cost if result.solved else "—")
    cols[4].metric("Expanded", result.expanded_nodes)
    st.caption(f"Visited: {result.visited_nodes} · Execution time: {result.execution_time * 1000:.3f} ms")
    if not result.solved:
        st.error("No path found.")


def animate_result(
    maze: Maze,
    result,
    speed: float,
    show_scores: bool,
    title: str = "",
    label=None,
    canvas=None,
) -> None:
    label = label if label is not None else st.empty()
    canvas = canvas if canvas is not None else st.empty()
    progress = st.progress(0, text=f"Preparing {result.algorithm} animation…")
    delay = max(0.0, speed)
    total_steps = max(1, len(result.explored_order) + len(result.path))
    completed_steps = 0
    explored: list[tuple[int, int]] = []
    for index, cell in enumerate(result.explored_order, start=1):
        explored.append(cell)
        label.caption(f"{title}{result.algorithm}: expanding {cell} ({index}/{len(result.explored_order)})")
        fig = maze_figure(
            maze, explored=explored, active=cell, scores=result.scores,
            show_scores=show_scores,
        )
        canvas.pyplot(fig, clear_figure=True, width="content")
        plt.close(fig)
        completed_steps += 1
        progress.progress(
            completed_steps / total_steps,
            text=f"Exploring · {index}/{len(result.explored_order)} nodes",
        )
        time.sleep(delay)
    shown_path: list[tuple[int, int]] = []
    for cell in result.path:
        shown_path.append(cell)
        label.caption(f"{title}{result.algorithm}: drawing final path")
        fig = maze_figure(
            maze, explored=explored, path=shown_path, active=cell,
            scores=result.scores, show_scores=show_scores,
        )
        canvas.pyplot(fig, clear_figure=True, width="content")
        plt.close(fig)
        completed_steps += 1
        progress.progress(
            completed_steps / total_steps,
            text=f"Drawing route · {len(shown_path)}/{len(result.path)} steps",
        )
        time.sleep(delay)
    label.caption(f"{title}{result.algorithm}: animation complete")
    progress.progress(1.0, text=f"{result.algorithm} animation complete ✓")
    time.sleep(min(delay, 0.08))
    progress.empty()


def run_all(maze: Maze):
    return [solver(maze.copy()) for solver in ALGORITHMS.values()]


def solver_tab(maze: Maze, algorithm: str, speed: float, show_scores: bool) -> None:
    st.subheader("Build the maze")
    edit_maze(maze, f"solver_editor_{st.session_state.editor_version}")
    show_legend()
    fig = maze_figure(maze)
    show_maze(fig)

    left, middle, right = st.columns(3)
    solve = left.button("▶ Solve Maze", type="primary", use_container_width=True)
    replay = middle.button("Replay Animation", use_container_width=True)
    if right.button("Reset Visualization", use_container_width=True):
        st.session_state.result = None

    if solve:
        st.session_state.result = ALGORITHMS[algorithm](maze.copy())
        animate_result(maze, st.session_state.result, speed, show_scores and algorithm == "A*")
    elif replay and st.session_state.result is not None:
        animate_result(maze, st.session_state.result, speed, show_scores and st.session_state.result.algorithm == "A*")

    result = st.session_state.result
    if result is not None:
        display_result(result)
        fig = maze_figure(
            maze,
            explored=result.explored_order,
            path=result.path,
            scores=result.scores,
            show_scores=show_scores and result.algorithm == "A*",
        )
        show_maze(fig)

    st.info(ALGORITHM_EXPLANATIONS[algorithm], icon="🧠")
    if st.button("Compare all algorithms on this maze"):
        st.session_state.comparison = run_all(maze)
    if st.session_state.comparison:
        st.dataframe(pd.DataFrame(result_row(item) for item in st.session_state.comparison), hide_index=True, use_container_width=True)


def move_human(direction: tuple[int, int]) -> None:
    maze = st.session_state.sim_maze
    if not st.session_state.human_active or maze is None:
        return
    row, col = st.session_state.human_path[-1]
    target = (row + direction[0], col + direction[1])
    if maze.is_open(target):
        st.session_state.human_path.append(target)
        if target == maze.goal:
            elapsed = time.perf_counter() - st.session_state.human_started
            st.session_state.human_active = False
            st.session_state.human_result = {
                "Method": "Human",
                "Solved?": "Yes",
                "Path Length": len(st.session_state.human_path) - 1,
                "Path Cost": len(st.session_state.human_path) - 1,
                "Expanded Nodes": "—",
                "Visited Nodes": len(set(st.session_state.human_path)),
                "Time (ms)": round(elapsed * 1000, 3),
            }


def handle_keyboard_event(event: dict[str, str] | None) -> None:
    """Route one new browser key event through the existing movement function."""

    if not event or not st.session_state.human_active:
        return
    event_id = event.get("id")
    if not event_id or event_id == st.session_state.last_keyboard_event:
        return
    st.session_state.last_keyboard_event = event_id
    direction = direction_for_key(event.get("key", ""))
    if direction is not None:
        move_human(direction)


def human_tab(maze: Maze, speed: float, show_scores: bool) -> None:
    st.subheader("Human vs AI Simulation")
    st.write("Start an attempt to freeze a copy of the current maze. Every AI algorithm then receives that exact same copy.")

    ai_col, human_col = st.columns(2, gap="large")

    with human_col:
        st.markdown("#### Human Attempt")
        if st.button("Start Human Attempt", type="primary"):
            st.session_state.sim_maze = maze.copy()
            st.session_state.human_path = [maze.start]
            st.session_state.human_started = time.perf_counter()
            st.session_state.human_active = maze.start != maze.goal
            st.session_state.human_result = None if maze.start != maze.goal else {
                "Method": "Human", "Solved?": "Yes", "Path Length": 0,
                "Path Cost": 0, "Expanded Nodes": "—", "Visited Nodes": 1,
                "Time (ms)": 0.0,
            }
            st.session_state.sim_results = None
            st.session_state.last_keyboard_event = None

        handle_keyboard_event(keyboard_event(active=st.session_state.human_active))

        active_maze = st.session_state.sim_maze or maze
        human_path = st.session_state.human_path
        current = human_path[-1] if human_path else active_maze.start
        fig = maze_figure(active_maze, human_path=human_path, current=current)
        show_maze(fig)
        show_legend()

        if st.session_state.human_active:
            elapsed = time.perf_counter() - st.session_state.human_started
            st.write(f"Current position: **{current}** · Moves: **{len(human_path) - 1}** · Time: **{elapsed:.2f} s**")
            st.caption(f"Current path: {human_path}")
            st.caption("Keyboard: Arrow Keys or WASD")
            _, up, _ = st.columns(3)
            up.button("↑ Up", on_click=move_human, args=((-1, 0),), use_container_width=True)
            left, down, right = st.columns(3)
            left.button("← Left", on_click=move_human, args=((0, -1),), use_container_width=True)
            down.button("↓ Down", on_click=move_human, args=((1, 0),), use_container_width=True)
            right.button("Right →", on_click=move_human, args=((0, 1),), use_container_width=True)
        elif st.session_state.human_result:
            st.success(f"Goal reached in {st.session_state.human_result['Path Length']} moves.")
        else:
            st.caption("Click Start Human Attempt to enable the movement controls.")

    with ai_col:
        st.markdown("#### AI Simulation")
        run_ai = st.button("Run AI Simulation", disabled=st.session_state.sim_maze is None)
        if run_ai:
            st.session_state.sim_results = run_all(active_maze)
            ai_label = st.empty()
            ai_canvas = st.empty()
            for result in st.session_state.sim_results:
                animate_result(
                    active_maze,
                    result,
                    speed,
                    show_scores and result.algorithm == "A*",
                    title="AI simulation · ",
                    label=ai_label,
                    canvas=ai_canvas,
                )
        elif st.session_state.sim_results:
            result = st.session_state.sim_results[-1]
            st.caption(f"Latest AI view: {result.algorithm}")
            fig = maze_figure(
                active_maze,
                explored=result.explored_order,
                path=result.path,
                scores=result.scores,
                show_scores=show_scores and result.algorithm == "A*",
            )
            show_maze(fig)
        else:
            fig = maze_figure(active_maze)
            show_maze(fig)

    if st.session_state.sim_results:
        rows = []
        if st.session_state.human_result:
            rows.append(st.session_state.human_result)
        elif human_path:
            elapsed = time.perf_counter() - st.session_state.human_started if st.session_state.human_started else 0
            rows.append({
                "Method": "Human", "Solved?": "No", "Path Length": len(human_path) - 1,
                "Path Cost": len(human_path) - 1, "Expanded Nodes": "—",
                "Visited Nodes": len(set(human_path)), "Time (ms)": round(elapsed * 1000, 3),
            })
        rows.extend(result_row(result) for result in st.session_state.sim_results)
        st.subheader("Same-maze comparison")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def sidebar_controls() -> tuple[str, float, bool]:
    with st.sidebar:
        st.header("Maze controls")
        maze = st.session_state.maze
        size = st.slider("Grid size", 5, 20, maze.rows)
        if size != maze.rows or size != maze.cols:
            replace_maze(Maze(size, size))
            st.rerun()

        cells = [(row, col) for row in range(maze.rows) for col in range(maze.cols)]
        start_col, goal_col = st.columns(2)
        selected_start = start_col.selectbox("Start cell", cells, index=cells.index(maze.start))
        selected_goal = goal_col.selectbox("Goal cell", cells, index=cells.index(maze.goal))
        if selected_start != maze.start or selected_goal != maze.goal:
            updated = Maze(maze.rows, maze.cols, selected_start, selected_goal, set(maze.walls))
            replace_maze(updated)
            st.rerun()

        example = st.selectbox("Predefined maze", ["Example 1 — Clear path", "Example 2 — Multiple routes"])
        if st.button("Load example", use_container_width=True):
            replace_maze(example_maze(example))
            st.rerun()

        density = st.slider("Wall density", 0.05, 0.45, 0.25, 0.05)
        solvable = st.checkbox("Guarantee a solvable maze", value=True)
        if st.button("Generate random maze", use_container_width=True):
            replace_maze(random_maze(size, size, density, solvable))
            st.rerun()

        if st.button("Clear all walls", use_container_width=True):
            replace_maze(Maze(size, size, maze.start, maze.goal))
            st.rerun()

        algorithm = st.selectbox("Algorithm", list(ALGORITHMS))
        speed_label = st.select_slider("Animation speed", ["Instant", "Fast", "Normal", "Slow"], value="Fast")
        speed = {"Instant": 0.0, "Fast": 0.015, "Normal": 0.06, "Slow": 0.15}[speed_label]
        show_scores = st.checkbox("Show A* g / h / f scores")
        st.caption("Movement is four-directional. Every move costs 1.")
    return algorithm, speed, show_scores


def main() -> None:
    st.set_page_config(page_title="CSBP301 AI Maze Solver", page_icon="🧭", layout="wide")
    init_state()
    apply_app_style()
    st.markdown(
        """
        <div class="maze-hero">
            <h1>🧭 CSBP301 AI Maze Solver</h1>
            <p>Watch intelligent search come alive — build, solve and compare paths in real time.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    algorithm, speed, show_scores = sidebar_controls()
    maze = st.session_state.maze
    solver, human = st.tabs(["AI Maze Solver", "Human vs AI Simulation"])
    with solver:
        solver_tab(maze, algorithm, speed, show_scores)
    with human:
        human_tab(maze, speed, show_scores)


if __name__ == "__main__":
    main()
