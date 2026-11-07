"""Streamlit host and mobile player interfaces for Class vs AI."""

from __future__ import annotations

from html import escape
from io import BytesIO
import os
from urllib.parse import urlencode, urlsplit, urlunsplit

import matplotlib.pyplot as plt
import pandas as pd
import qrcode
import streamlit as st

from arena.store import AVATARS, ArenaError, ArenaStore
from ui.keyboard_component import direction_for_key, keyboard_event
from ui.visualization import maze_figure


KEY_NAMES = {(-1, 0): "up", (1, 0): "down", (0, -1): "left", (0, 1): "right"}


def join_url(base_url: str, game_id: str) -> str:
    parsed = urlsplit(base_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ArenaError("Enter a complete base URL beginning with http:// or https://")
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme, parsed.netloc, path, urlencode({"arena": game_id}), ""))


def code_join_url(base_url: str) -> str:
    """Return the mobile landing page where a student can type a game code."""

    parsed = urlsplit(base_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ArenaError("Enter a complete base URL beginning with http:// or https://")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "join=1", ""))


def qr_image(url: str):
    qr = qrcode.QRCode(version=None, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#0f172a", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _show_maze(maze, path=None, current=None) -> None:
    fig = maze_figure(maze, path=path, human_path=path if current else None, current=current)
    st.pyplot(fig, width="content")
    plt.close(fig)


def _live_players(store: ArenaStore, game_id: str) -> None:
    """Show names and progress without inventing a rank for unfinished players."""

    players = store.players(game_id)
    game = store.get_game(game_id)
    finished = {player.token: index + 1 for index, player in enumerate(store.leaderboard(game_id))}
    rows = []
    for player in players:
        rows.append({
            "Place": finished.get(player.token, "—"),
            "Player": f"{AVATARS[player.character]} {player.nickname}",
            "Status": (
                "Finished" if player.completed
                else "Ready" if game.state == "LOBBY"
                else "Playing" if game.state == "PLAYING"
                else "Round ended"
            ),
            "Moves": player.moves,
            "Time": f"{player.elapsed:.1f}s" if player.start_time is not None else "—",
        })
    st.markdown("#### 👥 Live Players")
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.caption("Waiting for players to join…")


def _leaderboard(store: ArenaStore, game_id: str, *, show_ai: bool) -> None:
    game = store.get_game(game_id)
    leaders = store.leaderboard(game_id)
    st.subheader("🏁 Final Leaderboard")
    if not leaders:
        st.info("No player completed the maze.")
        return

    podium = st.columns(min(3, len(leaders)))
    for index, player in enumerate(leaders[:3]):
        medal = ["🥇", "🥈", "🥉"][index]
        with podium[index]:
            st.markdown(
                f"""
                <div class="arena-winner arena-winner-{index + 1}">
                    <div class="arena-medal">{medal}</div>
                    <div class="arena-avatar">{AVATARS[player.character]}</div>
                    <h3>{escape(player.nickname)}</h3>
                    <p>{player.moves} moves · {player.elapsed:.1f}s</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    for index, player in enumerate(leaders[3:], start=4):
        st.write(f"**#{index}** {AVATARS[player.character]} {player.nickname} — {player.moves} moves — {player.elapsed:.1f}s")

    if show_ai and game.ai_path:
        st.divider()
        st.subheader("🤖 Optional AI Comparison")
        st.metric("AI Algorithm", "A*")
        st.metric("AI Optimal Path", f"{game.ai_path_length} moves")
        _show_maze(game.maze, path=game.ai_path)
        matched = store.matched_ai(game_id)
        st.success(f"Matched the AI optimal path: {len(matched)} player(s)")
        if matched:
            st.write("Players who matched the AI: " + ", ".join(player.nickname for player in matched))


@st.fragment(run_every=1.0)
def host_live_panel(store: ArenaStore, game_id: str, url: str) -> None:
    try:
        game = store.get_game(game_id)
    except ArenaError as error:
        st.error(str(error))
        return
    counts = store.counts(game_id)
    st.markdown(f"## 🏆 CLASS VS AI · `{game.game_id}`")
    st.markdown(f"**Round status:** `{game.state}`")
    columns = st.columns(4)
    columns[0].metric("Players Joined", counts["joined"])
    columns[1].metric("Ready", counts["ready"])
    columns[2].metric("Playing", counts["playing"])
    columns[3].metric("Finished", counts["finished"])

    lobby, maze_col = st.columns([1, 1.35], gap="large")
    with lobby:
        st.image(qr_image(url), width=260)
        st.code(url, language=None)
        st.caption("Students scan the QR code or open this exact session link.")
        players = store.players(game_id)
        if players:
            st.markdown("#### Players")
            st.write("  ".join(f"{AVATARS[p.character]} **{p.nickname}**" for p in players))
    with maze_col:
        _show_maze(game.maze)

    _live_players(store, game_id)

    start, reveal, end, reset = st.columns(4)
    try:
        if start.button("▶ Start Round", type="primary", disabled=game.state != "LOBBY", use_container_width=True):
            store.start_round(game_id)
        if reveal.button("🤖 Reveal AI", disabled=game.state != "PLAYING", use_container_width=True):
            store.reveal(game_id)
        if end.button("⏹ End Round", disabled=game.state not in {"PLAYING", "REVEAL"}, use_container_width=True):
            store.end(game_id)
        if reset.button("↻ Reset Round", use_container_width=True):
            store.reset(game_id)
    except ArenaError as error:
        st.error(str(error))

    latest = store.get_game(game_id)
    if latest.state == "ENDED":
        celebration_key = f"arena_celebrated_{game_id}_{latest.ended_at}"
        if not st.session_state.get(celebration_key):
            st.session_state[celebration_key] = True
            st.balloons()
        _leaderboard(store, game_id, show_ai=bool(latest.ai_path))
    elif latest.state == "REVEAL":
        _leaderboard(store, game_id, show_ai=True)
    elif game.state == "PLAYING":
        st.info("The AI path and leaderboard are hidden while students are playing.")


def render_host_tab(maze, store: ArenaStore) -> None:
    st.subheader("🏆 Class vs AI — Live Maze Arena")
    st.write("Create one shared round, let the class join by phone, then end the round to celebrate the winners. AI comparison is optional.")
    if "arena_host_game" not in st.session_state:
        st.session_state.arena_host_game = None
    if st.button("Create New Class Game", type="primary", disabled=st.session_state.arena_host_game is not None):
        game = store.create_game(maze.copy())
        st.session_state.arena_host_game = game.game_id
    game_id = st.session_state.arena_host_game
    if not game_id:
        st.info("Create a game to generate the session ID, join link, and QR code.")
        return
    default_base = os.getenv("ARENA_BASE_URL", "https://csbp301-ai-maze-solver.streamlit.app/")
    base = st.text_input("Public app base URL", value=default_base, help="Set ARENA_BASE_URL in deployment when using another domain.")
    try:
        url = join_url(base, game_id)
    except ArenaError as error:
        st.error(str(error))
        return
    st.link_button("📱 Join by entering a game code", code_join_url(base), use_container_width=True)
    host_live_panel(store, game_id, url)
    if st.button("Close Host Dashboard"):
        st.session_state.arena_host_game = None
        st.rerun()


def _arena_keyboard(store: ArenaStore, game, player) -> None:
    key = f"arena_keyboard_{game.game_id}_{player.token[:6]}"
    seq_key = f"{key}_sequence"
    event_key = f"{key}_event"
    st.session_state.setdefault(seq_key, 0)
    st.session_state.setdefault(event_key, None)
    event = keyboard_event({
        "enabled": game.state == "PLAYING" and not player.completed,
        "attempt": f"{game.game_id}:{game.started_at}",
        "acknowledged": st.session_state[seq_key],
        "maze": {"rows": game.maze.rows, "cols": game.maze.cols, "start": list(game.maze.start), "goal": list(game.maze.goal), "walls": [list(c) for c in sorted(game.maze.walls)]},
        "path": [list(c) for c in player.path],
    })
    if not event or event.get("id") == st.session_state[event_key]:
        return
    st.session_state[event_key] = event.get("id")
    for item in event.get("events", []):
        sequence = item.get("sequence") if isinstance(item, dict) else None
        if not isinstance(sequence, int) or sequence <= st.session_state[seq_key]:
            continue
        st.session_state[seq_key] = sequence
        direction = direction_for_key(item.get("key", ""))
        if direction in KEY_NAMES:
            try:
                store.move_player(game.game_id, player.token, KEY_NAMES[direction])
            except ArenaError:
                break


@st.fragment(run_every=0.8)
def player_live_panel(store: ArenaStore, game_id: str, token: str) -> None:
    try:
        game, player = store.get_game(game_id), store.get_player(game_id, token)
    except ArenaError as error:
        st.error(str(error))
        return
    st.markdown(f"## {AVATARS[player.character]} {player.nickname}")
    if game.state in {"LOBBY", "STARTING"}:
        _arena_keyboard(store, game, player)
        st.success("You joined the arena.")
        st.info("Waiting for the host to start…")
        return
    _arena_keyboard(store, game, player)
    player = store.get_player(game_id, token)
    metrics = st.columns(2)
    metrics[0].metric("Moves", player.moves)
    metrics[1].metric("Status", "Finished" if player.completed else game.state.title())
    if game.state == "PLAYING" and not player.completed:
        st.caption("Keyboard: Arrow Keys or WASD")
        _, up, _ = st.columns(3)
        if up.button("↑", use_container_width=True, key="arena_up"):
            store.move_player(game_id, token, "up")
        left, down, right = st.columns(3)
        if left.button("←", use_container_width=True, key="arena_left"):
            store.move_player(game_id, token, "left")
        if down.button("↓", use_container_width=True, key="arena_down"):
            store.move_player(game_id, token, "down")
        if right.button("→", use_container_width=True, key="arena_right"):
            store.move_player(game_id, token, "right")
    elif player.completed:
        st.success(f"Maze complete: {player.moves} moves in {player.elapsed:.1f}s")
        if game.state == "PLAYING":
            st.info("Waiting for the host to reveal results…")
    if game.state in {"REVEAL", "ENDED"} and game.ai_path:
        st.info(f"A* optimal path: {game.ai_path_length} moves")
        if player.completed and player.moves == game.ai_path_length:
            st.success("You matched the AI optimal path!")


def render_player_page(store: ArenaStore, game_id: str, token: str | None) -> None:
    st.markdown("<div class='arena-player'></div>", unsafe_allow_html=True)
    st.markdown("<div class='maze-hero'><h1>🏆 Class vs AI</h1><p>Join the Maze Arena</p></div>", unsafe_allow_html=True)
    try:
        game = store.get_game(game_id)
    except ArenaError as error:
        st.error(str(error))
        return
    if token:
        player_live_panel(store, game.game_id, token)
        return
    if game.state != "LOBBY":
        st.error("This round has already started. Late joining is closed.")
        return
    with st.form("arena_join"):
        nickname = st.text_input("Nickname", max_chars=20)
        character = st.radio("Choose your character", list(AVATARS), horizontal=True, format_func=lambda name: f"{AVATARS[name]} {name}")
        submitted = st.form_submit_button("Join Arena", type="primary", use_container_width=True)
    if submitted:
        try:
            player = store.join_game(game.game_id, nickname, character)
        except ArenaError as error:
            st.error(str(error))
        else:
            st.query_params["arena"] = game.game_id
            st.query_params["player"] = player.token
            st.rerun()


def render_code_join_page(store: ArenaStore) -> None:
    """Mobile landing page for students who receive a game code verbally."""

    st.markdown("<div class='arena-player'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='maze-hero'><h1>🏆 Class vs AI</h1><p>Enter the game code shown by your teacher</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("arena_code_join"):
        game_id = st.text_input("Game Code", max_chars=12, placeholder="Example: A1B2C3")
        submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
    if submitted:
        game_id = game_id.strip().upper()
        try:
            game = store.get_game(game_id)
            if game.state != "LOBBY":
                raise ArenaError("This round has already started. Late joining is closed.")
        except ArenaError as error:
            st.error(str(error))
        else:
            st.query_params.clear()
            st.query_params["arena"] = game.game_id
            st.rerun()
