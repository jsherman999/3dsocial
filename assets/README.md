# assets/

Optional per-series images. Drop a file here and point a series at it in
`data.json`:

```json
{ "name": "Bluesky", "slot": 0, "lean": -8, "goon": 7.5, "prude": 2,
  "icon": "assets/bluesky.svg" }
```

The image shows up as a badge beside the series name in the editor card and in
the table view. It does **not** replace the 3D marker — plotly.js draws scene
markers from a fixed set of shapes and cannot use an arbitrary image as a
point in a rotating 3D scene, so each series keeps its color + shape + text
label out on the plot.

Badges render on a white plate, because most brand marks are monochrome and a
black logo would disappear in dark mode.

**No third-party logos are checked into this repo.** Company logos are
trademarks, and the terms for using them come from each company's own brand or
press page — that's where to get the official file and check what you're
allowed to do with it. Adding one is your call, not the repo's default.

Accepted paths are relative, inside the repo, and end in `.svg`, `.png`,
`.jpg`, `.webp`, or `.gif`. Anything else — an absolute path, a `..`, a URL,
or a `data:`/`javascript:` scheme — is dropped, since a chart definition can
arrive from a shared link.
