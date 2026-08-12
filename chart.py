"""Builds the rotatable 3-axis figure.

A chart definition carries N dimensions and a mapping of which three are on
x, y and z. Nothing here assumes a particular three, so adding a dimension is
a data.json edit rather than a code change.

Kept free of any web framework, so the same code serves the figure and the
generated browser page.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import plotly.graph_objects as go

from palette import MAX_SLOTS, THEMES, series_color, series_symbol

DATA_FILE = Path(__file__).with_name("data.json")

AXIS_ROLES = ("x", "y", "z")

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# Three-quarter view: enough perspective to read depth, not so much that the
# floor plane collapses.
DEFAULT_CAMERA = {
    "eye": {"x": 1.55, "y": 1.55, "z": 0.82},
    "up": {"x": 0, "y": 0, "z": 1},
    "center": {"x": 0, "y": 0, "z": -0.05},
}


def load_data(path: str | Path = DATA_FILE) -> dict[str, Any]:
    """Read a chart definition (dimensions + axis mapping + entities) from JSON."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def normalize_axes(axes: Any, dimensions: dict[str, Any]) -> dict[str, str]:
    """Coerce an x/y/z mapping into three distinct, known dimension keys."""
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for role in AXIS_ROLES:
        choice = (axes or {}).get(role)
        if choice not in dimensions or choice in used:
            choice = next(key for key in dimensions if key not in used)
        used.add(choice)
        mapping[role] = choice
    return mapping


def normalize(entities: Iterable[dict[str, Any]], dimensions: dict[str, Any]) -> list[dict[str, Any]]:
    """Coerce loose input into the shape the figure expects.

    Missing slots are assigned in order, every dimension is clamped to its own
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
        item: dict[str, Any] = {
            "name": (entity.get("name") or "").strip() or f"Series {slot + 1}",
            "slot": slot,
        }
        for key, spec in dimensions.items():
            item[key] = clamp(entity.get(key, midpoint(spec)), spec["min"], spec["max"])
        icon = safe_icon(entity.get("icon"))
        if icon:
            item["icon"] = icon
        result.append(item)
    return result


def midpoint(spec: dict[str, Any]) -> float:
    """Neutral start for a dimension an entity has no value for yet."""
    return (spec["min"] + spec["max"]) / 2


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


def ticks(low: float, high: float) -> list[float]:
    """A handful of round tick values -- never so many the cube looks ruled."""
    span = high - low
    step = next((s for s in (1, 2, 5, 10, 20, 50) if span / s <= 6), 100)
    values = []
    value = math.ceil(low / step) * step
    while value <= high + 1e-9:
        values.append(round(value, 6))
        value += step
    return values


def axis_spec(spec: dict[str, Any], tokens: dict, vertical: bool = False) -> dict:
    """Scene-axis config for one dimension.

    `vertical` adds headroom at the top: on z the point labels sit above their
    markers, and without the extra room the topmost one is clipped by the cube.
    """
    span = spec["max"] - spec["min"]
    pad = span * 0.06
    # Scene axis titles are rotated along the axis and render no inline markup,
    # so the range hint rides along on one line rather than in a styled span.
    return {
        "title": {
            "text": spec.get("axis_title", spec["label"]),
            "font": {"size": 12, "color": tokens["text_secondary"]},
        },
        "range": [
            spec["min"] - pad,
            spec["max"] + pad + (span * 0.10 if vertical else 0),
        ],
        "tickvals": ticks(spec["min"], spec["max"]),
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


def axis_specs(dimensions: dict[str, Any], theme: str) -> dict[str, dict[str, dict]]:
    """Every dimension's axis config, flat and vertical.

    The browser picks three of these per render, so moving a dimension onto a
    different axis needs no styling logic outside Python.
    """
    tokens = THEMES[theme]
    return {
        "flat": {key: axis_spec(spec, tokens) for key, spec in dimensions.items()},
        "vertical": {key: axis_spec(spec, tokens, vertical=True) for key, spec in dimensions.items()},
    }


def hover_template(dimensions: dict[str, Any], mapping: dict[str, str]) -> str:
    """Readout naming whichever three dimensions are currently plotted."""
    return (
        "<b>%{text}</b><br>"
        f"{dimensions[mapping['x']]['label']}: %{{x:.1f}}<br>"
        f"{dimensions[mapping['y']]['label']}: %{{y:.1f}}<br>"
        f"{dimensions[mapping['z']]['label']}: %{{z:.1f}}"
        "<extra></extra>"
    )


def point_trace(
    point: dict[str, Any],
    dimensions: dict[str, Any],
    mapping: dict[str, str],
    theme: str,
) -> dict[str, Any]:
    """One entity's marker + its direct label.

    The label is not decoration: the dark palette's closest pair sits in the
    6-8 CVD band and two light-mode hues fall under 3:1 on the surface, both of
    which are only legal with a second encoding channel. The name beside the
    dot is that channel, so it is never optional.
    """
    tokens = THEMES[theme]
    return {
        "type": "scatter3d",
        "x": [point[mapping["x"]]],
        "y": [point[mapping["y"]]],
        "z": [point[mapping["z"]]],
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
        "hovertemplate": hover_template(dimensions, mapping),
        "hoverlabel": {
            "bgcolor": tokens["surface"],
            "bordercolor": tokens["border"],
            "font": {"color": tokens["text_primary"], "family": FONT, "size": 12},
        },
    }


def stem_trace(
    points: list[dict[str, Any]],
    dimensions: dict[str, Any],
    mapping: dict[str, str],
    theme: str,
) -> dict[str, Any]:
    """Drop lines to the floor of the vertical axis.

    Depth is genuinely hard to read in a projected 3D scatter; the stems anchor
    each point to the floor so its position on the other two axes is legible
    without rotating. Hairline weight, chrome color -- scaffolding, not data.
    """
    tokens = THEMES[theme]
    floor = dimensions[mapping["z"]]["min"]
    x: list[Any] = []
    y: list[Any] = []
    z: list[Any] = []
    for point in points:
        x += [point[mapping["x"]], point[mapping["x"]], None]
        y += [point[mapping["y"]], point[mapping["y"]], None]
        z += [floor, point[mapping["z"]], None]
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


def trace_templates(dimensions: dict[str, Any], mapping: dict[str, str], theme: str) -> dict[str, Any]:
    """Empty, fully-styled traces for the browser build to clone and fill.

    Lets the static page add series and swap axes at runtime without a second
    copy of the styling rules living in JavaScript.
    """
    blank = {"name": "", "slot": 0, **{key: 0 for key in dimensions}}
    point = point_trace(blank, dimensions, mapping, theme)
    point.update({"x": [], "y": [], "z": [], "text": [], "name": ""})
    return {"point": point, "stem": stem_trace([], dimensions, mapping, theme)}


def base_layout(theme: str) -> dict[str, Any]:
    """The part of the layout that does not depend on which axes are shown."""
    tokens = THEMES[theme]
    return {
        "paper_bgcolor": tokens["surface"],
        "plot_bgcolor": tokens["surface"],
        "font": {"family": FONT, "color": tokens["text_primary"]},
        "margin": {"l": 0, "r": 0, "t": 8, "b": 8},
        "height": 600,
        "showlegend": True,
        "legend": {
            "orientation": "h",
            "yanchor": "top",
            "y": 1.0,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 12, "color": tokens["text_secondary"]},
            "bgcolor": "rgba(0,0,0,0)",
            "itemsizing": "constant",
        },
        "scene": {
            "camera": DEFAULT_CAMERA,
            "aspectmode": "cube",
            "bgcolor": tokens["surface"],
        },
        # Keeps the reader's camera angle when values or axes change under it.
        "uirevision": "keep-camera",
    }


def build_figure(
    entities: Iterable[dict[str, Any]],
    data: dict[str, Any] | None = None,
    theme: str = "light",
    show_stems: bool = True,
) -> go.Figure:
    """Rotatable 3D scatter: one trace per entity, plus recessive drop lines."""
    data = data or load_data()
    dimensions = data["dimensions"]
    mapping = normalize_axes(data.get("axes"), dimensions)
    points = normalize(entities, dimensions)

    figure = go.Figure()
    if show_stems and points:
        figure.add_trace(stem_trace(points, dimensions, mapping, theme))
    for point in points:
        figure.add_trace(point_trace(point, dimensions, mapping, theme))

    layout = base_layout(theme)
    specs = axis_specs(dimensions, theme)
    layout["scene"]["xaxis"] = specs["flat"][mapping["x"]]
    layout["scene"]["yaxis"] = specs["flat"][mapping["y"]]
    layout["scene"]["zaxis"] = specs["vertical"][mapping["z"]]
    figure.update_layout(**layout)
    return figure


GRAPH_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "toImageButtonOptions": {"filename": "three-axis-chart", "scale": 2},
    "modeBarButtonsToRemove": ["resetCameraLastSave3d"],
}
