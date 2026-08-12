"""Generate the standalone, fully interactive page (index.html).

The output is one file with no build step and no server: drag to rotate, edit
every value, add or remove series, switch themes, share a link that carries
your edits. It is what GitHub Pages serves.

All styling -- palette, chrome, axis config, trace specs -- is computed here in
Python and embedded as JSON, so the browser code only ever fills numbers into
pre-styled trace templates. There is no second copy of the design rules.

    python export.py                      # -> index.html, plotly.js from CDN
    python export.py --inline -o off.html # ~4.8 MB, opens with no network
    python export.py --data mine.json
"""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from string import Template
from typing import Any

import plotly.utils
from plotly.offline import get_plotlyjs, get_plotlyjs_version

from chart import AXIS_KEYS, GRAPH_CONFIG, build_figure, load_data, normalize, trace_templates
from palette import MAX_SLOTS, SERIES, SYMBOLS, THEMES, css

THEME_NAMES = ("light", "dark")

PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<meta name="description" content="${subtitle}">
<style>
${tokens}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--page); color: var(--text-primary);
  font-family: var(--font); line-height: 1.5;
}
.wrap { max-width: 1040px; margin: 0 auto; padding: 32px 24px 64px; }
header { margin-bottom: 20px; }
h1 { font-size: 22px; margin: 0 0 4px; font-weight: 600; }
p.sub { margin: 0; color: var(--text-secondary); font-size: 14px; max-width: 62ch; }
h2 { font-size: 14px; font-weight: 600; margin: 0 0 10px; color: var(--text-secondary); }

/* One control row, above everything it scopes. */
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 16px; }
.spacer { flex: 1 1 20px; }
button, .seg {
  font: inherit; font-size: 13px; color: var(--text-primary);
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
}
button { padding: 7px 13px; cursor: pointer; }
button:hover:not(:disabled) { border-color: var(--muted); }
button:disabled { opacity: .45; cursor: not-allowed; }
button:focus-visible, input:focus-visible { outline: 2px solid var(--muted); outline-offset: 2px; }
.seg { display: flex; gap: 2px; padding: 2px; }
.seg label { padding: 5px 11px; border-radius: 6px; cursor: pointer; color: var(--text-secondary);
  display: inline-flex; align-items: center; gap: 6px; }
.seg input { margin: 0; accent-color: var(--text-secondary); }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  padding: 8px; margin-bottom: 28px; overflow-x: auto; }
#chart { min-width: 520px; height: 600px; }

.cards { display: grid; gap: 14px; margin-bottom: 28px;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
.entity { background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px 16px; }
.entity-head { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.key { width: 10px; height: 10px; border-radius: 50%; flex: none; }
/* Badge for an optional per-series logo. The white plate is deliberate: most
   brand marks are monochrome and would vanish against one theme or the other. */
.badge { width: 20px; height: 20px; flex: none; border-radius: 4px; padding: 2px;
  background: #ffffff; border: 1px solid var(--border); object-fit: contain; }
.entity-head input[type=text] {
  font: inherit; font-size: 15px; font-weight: 600; flex: 1 1 auto; min-width: 0;
  color: var(--text-primary); background: transparent; padding: 4px 6px;
  border: 1px solid transparent; border-radius: 6px;
}
.entity-head input[type=text]:hover { border-color: var(--grid); }
.entity-head input[type=text]:focus { outline: none; border-color: var(--muted); }
.del { font-size: 17px; line-height: 1; color: var(--muted); background: none;
  border: none; padding: 2px 6px; }
.del:hover { color: var(--text-primary); background: none; }
.axis-row { display: flex; justify-content: space-between; align-items: baseline;
  font-size: 12px; color: var(--text-secondary); margin-top: 10px; }
.axis-row .val { font-variant-numeric: tabular-nums; color: var(--text-primary); }
/* Explicit track styling rather than accent-color: the native fallback paints
   the unfilled remainder differently per accent hue, which made otherwise
   identical sliders look like they meant different things. --fill is the
   percentage set on each input as it moves. */
input[type=range] { -webkit-appearance: none; appearance: none; width: 100%;
  height: 18px; margin: 3px 0 0; background: transparent; cursor: pointer; }
input[type=range]::-webkit-slider-runnable-track { height: 4px; border-radius: 2px;
  background: linear-gradient(90deg, var(--series) var(--fill), var(--grid) var(--fill)); }
input[type=range]::-moz-range-track { height: 4px; border-radius: 2px;
  background: linear-gradient(90deg, var(--series) var(--fill), var(--grid) var(--fill)); }
input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none;
  width: 15px; height: 15px; margin-top: -5.5px; border-radius: 50%;
  background: var(--surface); border: 2px solid var(--series); }
input[type=range]::-moz-range-thumb { width: 11px; height: 11px; border-radius: 50%;
  background: var(--surface); border: 2px solid var(--series); }
.ends { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); }

table { border-collapse: collapse; width: 100%; font-size: 14px;
  font-variant-numeric: tabular-nums; min-width: 460px; }
caption { text-align: left; font-size: 13px; color: var(--text-secondary); padding: 0 12px 8px; }
th, td { text-align: right; padding: 9px 12px; border-bottom: 1px solid var(--grid); }
th:first-child, td:first-child { text-align: left; }
thead th { color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--axis); }
tbody tr:last-child td, tbody tr:last-child th { border-bottom: none; }
th .key { display: inline-block; margin-right: 9px; vertical-align: baseline; }
th .badge { display: inline-block; margin-right: 9px; vertical-align: -5px; }
footer { color: var(--muted); font-size: 12px; }
footer a { color: var(--text-secondary); }
.toast { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%);
  background: var(--surface); color: var(--text-primary); border: 1px solid var(--border);
  border-radius: 8px; padding: 9px 16px; font-size: 13px; opacity: 0;
  transition: opacity .18s; pointer-events: none; }
.toast.show { opacity: 1; }
@media (prefers-reduced-motion: reduce) { .toast { transition: none; } }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>${title}</h1>
    <p class="sub">${subtitle}</p>
  </header>

  <div class="controls">
    <div class="seg">
      <label><input type="radio" name="theme" value="light">Light</label>
      <label><input type="radio" name="theme" value="dark">Dark</label>
    </div>
    <div class="seg">
      <label><input type="checkbox" id="spin">Spin</label>
      <label><input type="checkbox" id="stems" checked>Drop lines</label>
    </div>
    <div class="spacer"></div>
    <button id="add" type="button">Add series</button>
    <button id="reset" type="button">Reset</button>
    <button id="share" type="button">Copy link</button>
    <button id="download" type="button">Download JSON</button>
  </div>

  <div class="card"><div id="chart"></div></div>

  <h2>Values</h2>
  <div class="cards" id="cards"></div>

  <h2>Table view</h2>
  <div class="card" id="table"></div>

  <footer>
    Drag to rotate &middot; scroll to zoom &middot; shift-drag to pan.
    ${footnote} Edits are kept in this browser and travel in the &ldquo;Copy link&rdquo; URL.
  </footer>
</div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>${plotlyjs}</script>
<script>
(function () {
  "use strict";

  var AXES = ${axes};
  var AXIS_KEYS = ${axis_keys};
  var DEFAULTS = ${defaults};
  var SERIES = ${series};
  var SYMBOLS = ${symbols};
  var OVERFLOW = ${overflow};
  var MAX_SLOTS = ${max_slots};
  var LAYOUTS = ${layouts};
  var TEMPLATES = ${templates};
  var CONFIG = ${config};
  var STORE_KEY = "three-axis-chart";

  var gd = document.getElementById("chart");
  var cardsEl = document.getElementById("cards");
  var tableEl = document.getElementById("table");
  var toastEl = document.getElementById("toast");
  var spinBox = document.getElementById("spin");
  var stemsBox = document.getElementById("stems");

  var state = { entities: [], theme: null, stems: true };
  var spinTimer = null;

  // ---------------------------------------------------------------- helpers

  function clone(value) { return JSON.parse(JSON.stringify(value)); }

  function clamp(value, low, high) {
    var number = parseFloat(value);
    if (!isFinite(number)) { number = 0; }
    return Math.max(low, Math.min(high, number));
  }

  function colorFor(slot) {
    var ramp = SERIES[state.theme] || SERIES.light;
    return (slot >= 0 && slot < ramp.length) ? ramp[slot] : OVERFLOW[state.theme];
  }

  // Shape is the color-free half of a series' identity -- see palette.py.
  function symbolFor(slot) {
    return (slot >= 0 && slot < SYMBOLS.length) ? SYMBOLS[slot] : "circle-open";
  }

  // The series badge: an optional logo if the definition names one, otherwise
  // the color dot. Decorative either way -- the name always sits next to it.
  function keyFor(entity) {
    if (entity.icon) {
      var badge = document.createElement("img");
      badge.className = "badge";
      badge.src = entity.icon;
      badge.alt = "";
      return badge;
    }
    var dot = document.createElement("span");
    dot.className = "key";
    dot.style.background = colorFor(entity.slot);
    return dot;
  }

  function nextSlot() {
    var taken = {};
    state.entities.forEach(function (entity) { taken[entity.slot] = true; });
    for (var slot = 0; slot < MAX_SLOTS; slot++) {
      if (!taken[slot]) { return slot; }
    }
    return MAX_SLOTS;
  }

  // Names arrive from the URL hash and from typing. Angle brackets are dropped
  // so a name can never smuggle markup into a Plotly label, and every DOM
  // insertion below uses textContent.
  function cleanName(value, fallback) {
    var name = String(value == null ? "" : value).replace(/[<>]/g, "").trim().slice(0, 28);
    return name || fallback;
  }

  // Relative image paths only -- a definition can arrive from a shared link, so
  // anything carrying a scheme (javascript:, data:, off-site) is dropped.
  // ($$ is escaped for the Python template that emits this file.)
  var ICON_PATTERN = /^[A-Za-z0-9._\\/-]+\\.(?:svg|png|jpe?g|webp|gif)$$/i;

  function safeIcon(value) {
    if (typeof value !== "string") { return null; }
    var candidate = value.trim();
    if (!candidate || candidate.indexOf("..") !== -1 || candidate.charAt(0) === "/") { return null; }
    return ICON_PATTERN.test(candidate) ? candidate : null;
  }

  function sanitize(list) {
    var seen = {};
    var out = [];
    (Array.isArray(list) ? list : []).slice(0, MAX_SLOTS + 1).forEach(function (raw, index) {
      var slot = parseInt(raw && raw.slot, 10);
      if (!(slot >= 0) || slot > MAX_SLOTS || seen[slot]) { slot = index; }
      seen[slot] = true;
      var entity = { name: cleanName(raw && raw.name, "Series " + (slot + 1)), slot: slot };
      AXIS_KEYS.forEach(function (axis) {
        entity[axis] = clamp(raw && raw[axis], AXES[axis].min, AXES[axis].max);
      });
      var icon = safeIcon(raw && raw.icon);
      if (icon) { entity.icon = icon; }
      out.push(entity);
    });
    out.sort(function (a, b) { return a.slot - b.slot; });
    return out.length ? out : clone(DEFAULTS);
  }

  function toast(message) {
    toastEl.textContent = message;
    toastEl.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(function () { toastEl.classList.remove("show"); }, 1800);
  }

  // ------------------------------------------------------------------ state

  function readHash() {
    var match = /[#&]d=([^&]+)/.exec(window.location.hash || "");
    if (!match) { return null; }
    try { return sanitize(JSON.parse(decodeURIComponent(match[1]))); }
    catch (err) { return null; }
  }

  function readStore() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      return raw ? sanitize(JSON.parse(raw)) : null;
    } catch (err) { return null; }
  }

  function save() {
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(state.entities)); }
    catch (err) { /* private browsing -- the chart still works, edits just don't persist */ }
  }

  function initialTheme() {
    try {
      var stored = window.localStorage.getItem(STORE_KEY + ":theme");
      if (stored === "light" || stored === "dark") { return stored; }
    } catch (err) { /* fall through to the OS preference */ }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  // ------------------------------------------------------------------ chart

  function traces() {
    var out = [];
    var templates = TEMPLATES[state.theme];
    if (state.stems && state.entities.length) {
      var stem = clone(templates.stem);
      state.entities.forEach(function (entity) {
        stem.x.push(entity.lean, entity.lean, null);
        stem.y.push(entity.goon, entity.goon, null);
        stem.z.push(0, entity.prude, null);
      });
      out.push(stem);
    }
    state.entities.forEach(function (entity) {
      var trace = clone(templates.point);
      trace.x = [entity.lean];
      trace.y = [entity.goon];
      trace.z = [entity.prude];
      trace.name = entity.name;
      trace.text = [entity.name];
      trace.marker.color = colorFor(entity.slot);
      trace.marker.symbol = symbolFor(entity.slot);
      out.push(trace);
    });
    return out;
  }

  function drawChart() {
    // Both layouts share a uirevision, so redrawing after an edit or a theme
    // switch leaves the reader's camera exactly where they put it.
    Plotly.react(gd, traces(), LAYOUTS[state.theme], CONFIG);
  }

  // ------------------------------------------------------------- editor DOM

  function axisRow(entity, axis) {
    var spec = AXES[axis];
    var row = document.createElement("div");
    row.className = "axis-row";
    var label = document.createElement("span");
    label.textContent = spec.label;
    var value = document.createElement("span");
    value.className = "val";
    value.textContent = entity[axis].toFixed(1);
    row.appendChild(label);
    row.appendChild(value);

    var slider = document.createElement("input");
    slider.type = "range";
    slider.min = spec.min;
    slider.max = spec.max;
    slider.step = 0.5;
    slider.value = entity[axis];
    slider.setAttribute("aria-label", entity.name + " " + spec.label);

    function paint() {
      var pct = (entity[axis] - spec.min) / (spec.max - spec.min) * 100;
      slider.style.setProperty("--fill", pct.toFixed(1) + "%");
    }
    paint();

    slider.addEventListener("input", function () {
      entity[axis] = parseFloat(slider.value);
      value.textContent = entity[axis].toFixed(1);
      paint();
      drawChart();
      drawTable();
      save();
    });

    var ends = document.createElement("div");
    ends.className = "ends";
    var lowEnd = document.createElement("span");
    var highEnd = document.createElement("span");
    var parts = spec.hint.split("\\u2194");
    lowEnd.textContent = (parts[0] || "").trim();
    highEnd.textContent = (parts[1] || "").trim();
    ends.appendChild(lowEnd);
    ends.appendChild(highEnd);

    var group = document.createDocumentFragment();
    group.appendChild(row);
    group.appendChild(slider);
    group.appendChild(ends);
    return group;
  }

  function entityCard(entity) {
    var card = document.createElement("div");
    card.className = "entity";
    card.style.setProperty("--series", colorFor(entity.slot));

    var head = document.createElement("div");
    head.className = "entity-head";

    var name = document.createElement("input");
    name.type = "text";
    name.value = entity.name;
    name.maxLength = 28;
    name.setAttribute("aria-label", "series name");
    name.addEventListener("input", function () {
      entity.name = cleanName(name.value, "Series " + (entity.slot + 1));
      drawChart();
      drawTable();
      save();
    });

    var remove = document.createElement("button");
    remove.type = "button";
    remove.className = "del";
    remove.textContent = "\\u00d7";
    remove.setAttribute("aria-label", "remove " + entity.name);
    remove.addEventListener("click", function () {
      if (state.entities.length <= 1) { return; }
      state.entities = state.entities.filter(function (item) { return item !== entity; });
      render();
      save();
    });

    head.appendChild(keyFor(entity));
    head.appendChild(name);
    head.appendChild(remove);
    card.appendChild(head);
    AXIS_KEYS.forEach(function (axis) { card.appendChild(axisRow(entity, axis)); });
    return card;
  }

  function drawCards() {
    cardsEl.textContent = "";
    state.entities.forEach(function (entity) { cardsEl.appendChild(entityCard(entity)); });
    document.getElementById("add").disabled = state.entities.length >= MAX_SLOTS;
  }

  // The chart's readable twin: exact values, no hovering, no color needed.
  function drawTable() {
    var table = document.createElement("table");

    var caption = document.createElement("caption");
    caption.textContent = AXES.lean.label + ": " + AXES.lean.hint + " \\u00b7 other axes 0\\u201310";
    table.appendChild(caption);

    var head = document.createElement("tr");
    ["Series"].concat(AXIS_KEYS.map(function (axis) { return AXES[axis].label; }))
      .forEach(function (label) {
        var cell = document.createElement("th");
        cell.scope = "col";
        cell.textContent = label;
        head.appendChild(cell);
      });
    var thead = document.createElement("thead");
    thead.appendChild(head);
    table.appendChild(thead);

    var body = document.createElement("tbody");
    state.entities.forEach(function (entity) {
      var row = document.createElement("tr");
      var label = document.createElement("th");
      label.scope = "row";
      label.appendChild(keyFor(entity));
      label.appendChild(document.createTextNode(entity.name));
      row.appendChild(label);
      AXIS_KEYS.forEach(function (axis) {
        var cell = document.createElement("td");
        cell.textContent = entity[axis].toFixed(1);
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    table.appendChild(body);

    tableEl.textContent = "";
    tableEl.appendChild(table);
  }

  function render() {
    drawChart();
    drawCards();
    drawTable();
  }

  // ------------------------------------------------------------------ wiring

  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.dataset.theme = theme;
    document.querySelector('input[name=theme][value=' + theme + ']').checked = true;
    try { window.localStorage.setItem(STORE_KEY + ":theme", theme); } catch (err) { /* ignore */ }
    render();
  }

  Array.prototype.forEach.call(document.querySelectorAll("input[name=theme]"), function (radio) {
    radio.addEventListener("change", function () { applyTheme(radio.value); });
  });

  stemsBox.addEventListener("change", function () {
    state.stems = stemsBox.checked;
    drawChart();
  });

  // Orbits whatever camera the reader already has: their zoom and elevation
  // survive, only the azimuth advances.
  spinBox.addEventListener("change", function () {
    clearInterval(spinTimer);
    if (!spinBox.checked) { return; }
    spinTimer = setInterval(function () {
      var scene = (gd.layout && gd.layout.scene) || {};
      var eye = (scene.camera && scene.camera.eye) || { x: 1.75, y: 1.75, z: 0.95 };
      var radius = Math.sqrt(eye.x * eye.x + eye.y * eye.y);
      var angle = Math.atan2(eye.y, eye.x) + 0.012;
      Plotly.relayout(gd, {
        "scene.camera.eye": { x: radius * Math.cos(angle), y: radius * Math.sin(angle), z: eye.z }
      });
    }, 45);
  });

  document.getElementById("add").addEventListener("click", function () {
    if (state.entities.length >= MAX_SLOTS) { return; }
    var slot = nextSlot();
    state.entities.push({ name: "Series " + (slot + 1), slot: slot, lean: 0, goon: 5, prude: 5 });
    state.entities.sort(function (a, b) { return a.slot - b.slot; });
    render();
    save();
  });

  document.getElementById("reset").addEventListener("click", function () {
    state.entities = clone(DEFAULTS);
    if (window.location.hash) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    render();
    save();
    toast("Reset to defaults");
  });

  document.getElementById("share").addEventListener("click", function () {
    var url = window.location.origin + window.location.pathname + window.location.search
      + "#d=" + encodeURIComponent(JSON.stringify(state.entities));
    history.replaceState(null, "", url);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(
        function () { toast("Link copied \\u2014 it carries your values"); },
        function () { toast("Copy failed \\u2014 the URL bar now holds your values"); }
      );
    } else {
      toast("The URL bar now holds your values");
    }
  });

  document.getElementById("download").addEventListener("click", function () {
    var payload = JSON.stringify({ axes: AXES, entities: state.entities }, null, 2);
    var url = URL.createObjectURL(new Blob([payload], { type: "application/json" }));
    var link = document.createElement("a");
    link.href = url;
    link.download = "chart-data.json";
    link.click();
    URL.revokeObjectURL(url);
  });

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (event) {
    try { if (window.localStorage.getItem(STORE_KEY + ":theme")) { return; } } catch (err) { /* ignore */ }
    applyTheme(event.matches ? "dark" : "light");
  });

  // A link's values win over this browser's saved edits, which win over the
  // defaults baked in at build time.
  state.entities = readHash() || readStore() || clone(DEFAULTS);
  state.stems = stemsBox.checked;
  applyTheme(initialTheme());
})();
</script>
</body>
</html>
""")


def build_page(
    data: dict[str, Any],
    title: str,
    subtitle: str,
    footnote: str = "",
    inline_js: bool = False,
) -> str:
    """Render the whole interactive page as a single HTML string."""
    axes = data["axes"]
    entities = normalize(data["entities"])

    def dumps(value: Any) -> str:
        return json.dumps(value, cls=plotly.utils.PlotlyJSONEncoder)

    # Layouts carry no data, so one per theme covers every edit the reader makes.
    layouts = {
        theme: build_figure([], axes, theme=theme).to_plotly_json()["layout"]
        for theme in THEME_NAMES
    }

    page = PAGE.substitute(
        title=escape(title),
        subtitle=escape(subtitle, quote=True),
        footnote=escape(footnote),
        tokens=css(),
        axes=dumps(axes),
        axis_keys=dumps(list(AXIS_KEYS)),
        defaults=dumps(entities),
        series=dumps({
            "light": [pair[0] for pair in SERIES],
            "dark": [pair[1] for pair in SERIES],
        }),
        symbols=dumps(SYMBOLS),
        overflow=dumps({theme: THEMES[theme]["overflow"] for theme in THEME_NAMES}),
        max_slots=MAX_SLOTS,
        layouts=dumps(layouts),
        templates=dumps({theme: trace_templates(axes, theme) for theme in THEME_NAMES}),
        config=dumps(GRAPH_CONFIG),
        plotlyjs=get_plotlyjs() if inline_js else "",
    )

    if not inline_js:
        page = page.replace(
            "<script></script>",
            f'<script src="https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js" '
            'charset="utf-8"></script>',
        )
    return page


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-o", "--out", default="index.html", help="output file (default: index.html)")
    parser.add_argument("--data", default=None, help="chart definition JSON (default: data.json)")
    parser.add_argument("--inline", action="store_true", help="embed plotly.js (~4.8 MB, works offline)")
    parser.add_argument("--title", default="Prudishness / lean / goonishness")
    parser.add_argument(
        "--subtitle",
        default=(
            "The 2x2 forces a trade-off that isn't real: a platform can be prudish "
            "and goonish at the same time. Three independent axes let it be both."
        ),
    )
    parser.add_argument("--footnote", default="Values are editable starting points, not measurements.")
    args = parser.parse_args()

    data = load_data(args.data) if args.data else load_data()
    out = Path(args.out)
    out.write_text(
        build_page(data, args.title, args.subtitle, args.footnote, inline_js=args.inline),
        encoding="utf-8",
    )
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB, "
          f"plotly.js {'inlined' if args.inline else 'from CDN'})")


if __name__ == "__main__":
    main()
