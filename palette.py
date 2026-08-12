"""Color and chrome tokens for the 3-axis chart.

Single source of truth for both the Plotly figure (server-side) and the page
chrome (CSS injected into the Dash index template and the standalone export).

The categorical slots below were checked with an OKLab/CVD palette validator in
*all-pairs* mode -- the right mode for scatter, where every series can sit next
to every other one -- against each theme's own surface:

    light  #2a78d6 #eda100 #e87ba4 #008300
           worst-pair CVD dE 13.0, normal-vision dE 19.6
           yellow (2.11:1) and magenta (2.62:1) fall under 3:1 on the light
           surface, so the chart always ships visible point labels *and* the
           table view underneath it.
    dark   #3987e5 #c98500 #d55181 #008300
           worst-pair CVD dE 6.9 (green vs yellow, protan), normal-vision 19.3
           the 6-8 band is only legal alongside a second encoding channel --
           here every point carries its name as a direct label.

Slots 5-8 are the remaining hues from the same ramp. They clear the *adjacent*
pair gates but not all-pairs, so a chart using more than four series leans on
the direct labels for identity. Past slot 8 nothing is generated or cycled:
extra entities take the neutral "overflow" color.
"""

LIGHT = {
    "name": "light",
    "surface": "#fcfcfb",     # chart surface
    "page": "#f9f9f7",        # page plane behind the chart
    "text_primary": "#0b0b0b",
    "text_secondary": "#52514e",
    "muted": "#898781",       # axis labels
    "grid": "#e1e0d9",        # hairline gridlines
    "axis": "#c3c2b7",        # baseline / zero rules
    "border": "rgba(11,11,11,0.10)",
    "overflow": "#898781",    # 9th+ entity, never a generated hue
}

DARK = {
    "name": "dark",
    "surface": "#1a1a19",
    "page": "#0d0d0d",
    "text_primary": "#ffffff",
    "text_secondary": "#c3c2b7",
    "muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "border": "rgba(255,255,255,0.10)",
    "overflow": "#898781",
}

THEMES = {"light": LIGHT, "dark": DARK}

# (light, dark) pairs. Index == color slot. Slots 0-3 are all-pairs validated.
SERIES = [
    ("#2a78d6", "#3987e5"),  # 0 blue
    ("#eda100", "#c98500"),  # 1 yellow
    ("#e87ba4", "#d55181"),  # 2 magenta
    ("#008300", "#008300"),  # 3 green
    ("#eb6834", "#d95926"),  # 4 orange    -- adjacent-validated only
    ("#1baf7a", "#199e70"),  # 5 aqua      -- adjacent-validated only
    ("#4a3aa7", "#9085e9"),  # 6 violet    -- adjacent-validated only
    ("#e34948", "#e66767"),  # 7 red       -- adjacent-validated only
]

MAX_SLOTS = len(SERIES)

# Marker shape is a second, color-free identity channel. It is what makes the
# dark palette's closest pair (green vs yellow, CVD dE 6.9) legal, and it keeps
# the points apart in print, in forced-colors mode, and in a grayscale
# screenshot. Ordered so the first four are the most distinct silhouettes.
SYMBOLS = ["circle", "square", "diamond", "cross", "x", "circle-open", "square-open", "diamond-open"]


def series_symbol(slot: int) -> str:
    """Marker shape for a slot. Pairs with the color, never replaces it."""
    if slot < 0 or slot >= len(SYMBOLS):
        return "circle-open"
    return SYMBOLS[slot]


def series_color(slot: int, theme: str = "light") -> str:
    """Color for a categorical slot. Slots follow the entity, never its rank."""
    tokens = THEMES[theme]
    if slot < 0 or slot >= MAX_SLOTS:
        return tokens["overflow"]
    return SERIES[slot][0 if theme == "light" else 1]


def css(font_stack: str = 'system-ui, -apple-system, "Segoe UI", sans-serif') -> str:
    """Page chrome as CSS custom properties, generated from the tokens above."""

    def block(tokens):
        return "\n".join(
            f"  --{key}: {value};"
            for key, value in tokens.items()
            if key != "name"
        )

    return f"""
:root {{
  color-scheme: light;
{block(LIGHT)}
  --font: {font_stack};
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
{block(DARK)}
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
{block(DARK)}
}}
"""
