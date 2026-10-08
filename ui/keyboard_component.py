"""Tiny local Streamlit component for Human mode keyboard input."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components


_keyboard_component = components.declare_component(
    "maze_keyboard_controls",
    path=str(Path(__file__).with_name("keyboard_frontend")),
)


KEY_DIRECTIONS = {
    "ArrowUp": (-1, 0),
    "w": (-1, 0),
    "ArrowDown": (1, 0),
    "s": (1, 0),
    "ArrowLeft": (0, -1),
    "a": (0, -1),
    "ArrowRight": (0, 1),
    "d": (0, 1),
}


def direction_for_key(key: str) -> tuple[int, int] | None:
    """Translate an arrow/WASD key into the existing movement direction."""

    normalized = key if key.startswith("Arrow") else key.lower()
    return KEY_DIRECTIONS.get(normalized)


def keyboard_event(active: bool):
    """Return the latest browser key event while a human attempt is active."""

    return _keyboard_component(active=active, default=None, key="human_keyboard")

