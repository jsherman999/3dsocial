# 3dsocial

**→ [jsherman999.github.io/3dsocial](https://jsherman999.github.io/3dsocial/)**

A 2×2 political-compass meme forces a trade-off that isn't real. Putting
"prudish" at the top and "gooner" at the bottom of one axis says a platform
must be one or the other — but a platform can be both at once, and several
obviously are. That's not one axis with two ends. It's two axes.

So this is the same joke with the trade-off removed: **political lean**,
**goonishness**, and **prudishness** as three independent axes, drawn as a
rotatable 3D scatter you can edit in the browser.

<img src="docs/preview.png" alt="The chart in dark mode: four labeled points in a rotatable 3D cube, with editor cards below" width="820">

## Using it

Open the [live page](https://jsherman999.github.io/3dsocial/). Nothing to
install and nothing runs on a server — it's one static HTML file.

- **Drag to rotate**, scroll to zoom, shift-drag to pan. **Spin** orbits it for
  you, starting from wherever you left the camera.
- **Edit any value** with the sliders under the chart. Rename a series, or use
  **Add series** / **×** to change who's on it (up to 8).
- **Copy link** puts your edits in the URL, so you can send someone the chart
  as you arranged it. Your edits also persist in your own browser until you hit
  **Reset**.
- **Light and dark** both ship. The page follows your OS setting on first load;
  the toggle overrides it and is remembered.
- **Drop lines** connect each point down to the floor plane. A projected 3D
  scatter is genuinely ambiguous about depth, and the stems are what let you
  read a point's lean/goon position without rotating.

The starting values are opinionated guesses meant to be argued with, not
measurements. That's the point of making them editable.

## Editing the defaults

`data.json` holds the axes and the starting series:

```json
{ "name": "Tumblr", "slot": 3, "lean": -8.0, "goon": 7.0, "prude": 7.5 }
```

`slot` is the color/shape slot and stays with the series for good, so deleting
one never repaints the others. `lean` runs −10 to +10; `goon` and `prude` run
0 to 10.

Then rebuild the page:

```bash
pip install -r requirements.txt
python export.py                 # writes index.html
```

Pushing to `main` also rebuilds and redeploys it (`.github/workflows/pages.yml`).

### Turning Pages on

One manual step, once: **Settings → Pages → Source: GitHub Actions**. Enabling
Pages for the first time needs a repo-settings permission the workflow token
doesn't have, so the workflow can't do it for you — it skips the deploy and
says so until the switch is flipped.

("Deploy from a branch" → `main` → `/ (root)` works too, since `index.html` is
committed. You just lose the automatic rebuild from `data.json`.)

Other options:

```bash
python export.py --inline -o offline.html   # embeds plotly.js (~4.8 MB), no network needed
python export.py --data mine.json           # build from a different definition
python export.py --title "..." --subtitle "..."
```

`--inline` is the one to use for a file you want to email or open on a plane.
The default build pulls plotly.js from a CDN and is ~30 KB.

## Files

| | |
|---|---|
| `index.html` | the generated page — this is what Pages serves |
| `export.py` | builds `index.html`; owns the page shell and the browser code |
| `chart.py` | builds the plotly figure and the trace templates |
| `palette.py` | colors, shapes, and chrome tokens for both themes |
| `data.json` | axes and starting values |
| `assets/` | optional per-series images ([see notes](assets/README.md)) |

All the styling lives in Python and is embedded into the page as JSON. The
browser code only fills numbers into pre-styled trace templates, so there is no
second copy of the design rules to drift out of sync.

## About the logos

The original meme used company logos. This doesn't, for two reasons.

The technical one: plotly.js draws 3D scene markers from a fixed set of shapes
and can't place an arbitrary image at a point in a rotating scene. Anything
logo-shaped out on the plot would have to be an HTML overlay reprojected on
every frame, which breaks the moment you rotate.

The other one: they're trademarks, and the terms come from each company's own
brand page. So the repo ships the *hook* rather than the files — add an `icon`
path to a series and it shows up as a badge in the editor and the table view.
See [`assets/README.md`](assets/README.md).

Out on the plot, each series is identified three ways instead: color, marker
shape, and its name printed next to the point.

## Design notes

- **The palette is validated, not eyeballed.** The four colors clear
  lightness-band, chroma, colorblind-separation, and contrast checks against
  each theme's own surface, in *all-pairs* mode — the right mode for a scatter,
  where any series can end up next to any other. Details and measurements are
  in `palette.py`.
- **Shape is a second identity channel.** The dark palette's closest pair sits
  in the marginal band for red-green colorblindness, and two light-mode hues
  fall below 3:1 against the surface. Distinct marker shapes plus the printed
  name are what make that safe, which is also why the point labels are always
  on.
- **There's a table view** under the chart with every exact value, so nothing
  is reachable only by hovering or only by color.
