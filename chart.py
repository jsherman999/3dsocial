"""Builds the rotatable 3-axis figure.

Kept free of Dash so the same figure code serves the interactive app and the
standalone HTML export.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import plotly.graph_objects as go

from palette import MAX_SLOTS, THEMES, series_color, series_symbol

DATA_FILE = Path(__file__).with_name("data.json")

AXIS_KEYS = ("lean", "goon", "prude")

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# Three-quarter view: enough perspective to read depth, not so much that the
# floor plane collapses.
DEFAULT_CAMERA = {
    "eye": {"x": 1.55, "y": 1.55, "z": 0.82},
    "up": {"x": 0, "y": 0, "z": 1},
    "center": {"x": 0, "y": 0, "z": -0.05},
}


def load_data(path: str | Path = DATA_FILE) -> dict[str, Any]:
    """Read a chart definition (axes + entities) from JSON."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def normalize(entities: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Coerce loose input into the shape the figure expects.

    Missing slots are assigned in order, values are clamped to their axis
    range, and blank names fall back to a placeholder so a point is never
    unlabeled (the labels are what carry identity for colorblind readers).
    """
    result: list[dict[str, Any]] = []
    used: set[int] = set()
    for entity in entities:
        slot = entity.get("slot")
        if not isinstance(slot, int) or slot < 0 or slot in used:
            slot = next_slot(used)
        used.add(slot)
        item = {
            "name": (entity.get("name") or "").strip() or f"Series {slot + 1}",
            "slot": slot,
            "lean": clamp(entity.get("lean", 0), -10, 10),
            "goon": clamp(entity.get("goon", 5), 0, 10),
            "prude": clamp(entity.get("prude", 5), 0, 10),
        }
        icon = safe_icon(entity.get("icon"))
        if icon:
            item["icon"] = icon
        result.append(item)
    return result


# Relative image paths only. Chart definitions can arrive from a shared link,
# so anything with a scheme -- javascript:, data:, an off-site URL -- is dropped
# rather than rendered.
ICON_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+\.(?:svg|png|jpe?g|webp|gif)$", re.IGNORECASE)


def safe_icon(value: Any) -> str | None:
    """Accept a local image path for a series badge, reject everything else."""
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate or ".." in candidate or candidate.startswith("/"):
        return None
    return candidate if ICON_PATTERN.match(candidate) else None


def next_slot(used: Iterable[int]) -> int:
    """Lowest free color slot, so a deleted entity never repaints the others."""
    taken = set(used)
    for slot in range(MAX_SLOTS):
        if slot not in taken:
            return slot
    return MAX_SLOTS  # overflow -> neutral color, never a generated hue


def clamp(value: Any, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(low, min(high, number))


def _axis(spec: dict[str, Any], rng: list[float], ticks: list[float], tokens: dict) -> dict:
    # Scene axis titles are rotated along the axis and render no inline markup,
    # so the range hint rides along on one line rather than in a styled span.
    return {
        "title": {
            "text": spec.get("axis_title", spec["label"]),
            "font": {"size": 12, "color": tokens["text_secondary"]},
        },
        "range": rng,
        "tickvals": ticks,
        "tickfont": {"size": 11, "color": tokens["muted"]},
        "gridcolor": tokens["grid"],
        "gridwidth": 1,
        "zeroline": True,
        "zerolinecolor": tokens["axis"],
        "zerolinewidth": 2,
        "showbackground": True,
        "backgroundcolor": tokens["page"],
        "showspikes": False,
    }


def point_trace(point: dict[str, Any], axes: dict[str, Any], theme: str) -> dict[str, Any]:
    """One entity's marker + its direct label.

    The label is not decoration: the dark palette's closest pair sits in the
    6-8 CVD band and two light-mode hues fall under 3:1 on the surface, both of
    which are only legal with a second encoding channel. The name beside the
    dot is that channel, so it is never optional.
    """
    tokens = THEMES[theme]
    return {
        "type": "scatter3d",
        "x": [point["lean"]],
        "y": [point["goon"]],
        "z": [point["prude"]],
        "mode": "markers+text",
        "name": point["name"],
        "text": [point["name"]],
        "textposition": "top center",
        # Label ink stays a text token -- the marker beside it carries the
        # identity color.
        "textfont": {"size": 13, "color": tokens["text_primary"], "family": FONT},
        "marker": {
            "size": 11,
            "symbol": series_symbol(point["slot"]),
            "color": series_color(point["slot"], theme),
            # A 2px surface ring instead of a border, so overlapping points
            # separate without an outline reading as data.
            "line": {"color": tokens["surface"], "width": 2},
        },
        "hovertemplate": (
            "<b>%{text}</b><br>"
            f"{axes['lean']['label']}: %{{x:.1f}}<br>"
            f"{axes['goon']['label']}: %{{y:.1f}}<br>"
            f"{axes['prude']['label']}: %{{z:.1f}}"
            "<extra></extra>"
        ),
        "hoverlabel": {
            "bgcolor": tokens["surface"],
            "bordercolor": tokens["border"],
            "font": {"color": tokens["text_primary"], "family": FONT, "size": 12},
        },
    }


def stem_trace(points: list[dict[str, Any]], theme: str) -> dict[str, Any]:
    """Drop lines to the prudishness=0 plane.

    Depth is genuinely hard to read in a projected 3D scatter; the stems anchor
    each point to the floor so its lean/goon position is legible without
    rotating. Hairline weight, chrome color -- scaffolding, not data.
    """
    tokens = THEMES[theme]
    x: list[Any] = []
    y: list[Any] = []
    z: list[Any] = []
    for point in points:
        x += [point["lean"], point["lean"], None]
        y += [point["goon"], point["goon"], None]
        z += [0, point["prude"], None]
    return {
        "type": "scatter3d",
        "x": x,
        "y": y,
        "z": z,
        "mode": "lines",
        "line": {"color": tokens["axis"], "width": 2},
        "hoverinfo": "skip",
        "showlegend": False,
    }


def trace_templates(axes: dict[str, Any], theme: str) -> dict[str, Any]:
    """Empty, fully-styled traces for the browser build to clone and fill.

    Lets the static page add and recolor series at runtime without a second
    copy of the styling rules living in JavaScript.
    """
    blank = {"name": "", "slot": 0, "lean": 0, "goon": 0, "prude": 0}
    point = point_trace(blank, axes, theme)
    point.update({"x": [], "y": [], "z": [], "text": [], "name": ""})
    return {"point": point, "stem": stem_trace([], theme)}


def build_figure(
    entities: Iterable[dict[str, Any]],
    axes: dict[str, Any] | None = None,
    theme: str = "light",
    show_stems: bool = True,
) -> go.Figure:
    """Rotatable 3D scatter: one trace per entity, plus recessive drop lines."""
    tokens = THEMES[theme]
    axes = axes or load_data()["axes"]
    points = normalize(entities)

    figure = go.Figure()
    if show_stems and points:
        figure.add_trace(stem_trace(points, theme))
    for point in points:
        figure.add_trace(point_trace(point, axes, theme))

    figure.update_layout(
        template=None,
        paper_bgcolor=tokens["surface"],
        plot_bgcolor=tokens["surface"],
        font={"family": FONT, "color": tokens["text_primary"]},
        margin={"l": 0, "r": 0, "t": 8, "b": 8},
        height=600,
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": 1.0,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 12, "color": tokens["text_secondary"]},
            "bgcolor": "rgba(0,0,0,0)",
            "itemsizing": "constant",
        },
        scene={
            "camera": DEFAULT_CAMERA,
            "aspectmode": "cube",
            "bgcolor": tokens["surface"],
            "xaxis": _axis(axes["lean"], [-11, 11], [-10, -5, 0, 5, 10], tokens),
            "yaxis": _axis(axes["goon"], [-0.6, 11], [0, 2, 4, 6, 8, 10], tokens),
            "zaxis": _axis(axes["prude"], [-0.6, 11.6], [0, 2, 4, 6, 8, 10], tokens),
        },
        # Keeps the reader's camera angle when values change underneath it.
        uirevision="keep-camera",
    )
    return figure


GRAPH_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {"filename": "three-axis-chart", "scale": 2},
    "modeBarButtonsToRemove": ["resetCameraLastSave3d"],
}
