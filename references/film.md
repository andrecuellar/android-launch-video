# The film

Read the product-launch-motion files listed in `SKILL.md` first: this page only covers what the
Android adaptation adds and the contract the tools expect.

## Order of work

1. `DIRECTION.md`: brand (colors and fonts taken from the app theme, logo), concept, the script by
   bars on the measured beat grid, and the rules of `SKILL.md` section 2.
2. `PLAN.md`: scene by scene, which recorded clip plays, what lifts off the screen, which cue fires.
3. Storyboard key frames drawn with Playwright, looked at, then shown for approval.
4. Code.

## From recordings to material

```bash
video/scripts/clips60.sh            # clips60/*.mp4 + *.taps.json -> video/material60/
```

`clips.py` extracts every unique frame of each clip to `<material>/frames/<clip>/NNNNN.jpg` (scaled
to 1080x2400 if needed) and writes `<material>/clips.js`:

```js
const CLIPS = { "<clip>": { "n": 1234, "times": [0, 0.0167, ...], "taps": [...], "duration": 20.5 } };
```

The film shows, at film time `t`, the last frame whose pts is `<= t` (clip time). Clips whose name
ends in `-discard` are skipped. `motion.py` writes `<material>/motion.json`
(`{clip: {"d": [diff per frame], "motion": [[t0, t1], ...], "threshold": 2.0}}`); `still.py` and
`settled.py` find still and settled moments to hold on; `period.py` measures the loop period of an
in-app animation so a time jump of a whole number of periods is invisible.

## The film page contract

The film lives in `video/film/index.html` and is written per production (not bundled). It loads
`core.js`, `../material60/clips.js` and its fonts from `video/film/assets/`. Formats:
`index.html?f=16x9` (1920x1080) and `?f=9x16` (1080x1920). The checks and renderers expect:

| Global | Meaning |
| --- | --- |
| `window.READY` | Promise or value awaited after load (fonts, images decoded). |
| `window.DUR` | Film length in seconds. |
| `window.seek(t)` | Draws the frame at time `t`. Pure: same `t`, same pixels, in any order. May be async. |
| `window.CUES` | Sound cues `{t, type, ...extra}`, built with `cue(t, type, extra)` from `core.js`. Read by `audio.py` through `snap.mjs ... --cues cues.json`. Cue types: `references/audio.md`. |
| `window.boxes(t)` | Layout at `t` for `overlaps.mjs`, `boxes.mjs`, `point.mjs`: `{screen: [x0,y0,x1,y1] or null, bands: [{box}], popouts: [{name, box, opaque, flying, op}], texts: [{name, box, op}], ribbons?: [{k, poly}], center?: {axis, elements: [{name, box}]}}`. Texts named `... line N` / `... word N` are grouped as one. |
| `window.screenAt()` | The 4 corners of the phone screen in the frame, or null (`screens.mjs`). |
| `window.sourceAt(t)` | `{clip, tc, shot, fade, hidden}`: which recording frame is on the phone (`screens.mjs`). |
| `window.measureReading(dt)` | `[{name, best, from, to}]` reading windows per text (`reading.mjs`). |

DOM ids and classes used by tools: `#world` and `#phone` (`transform.mjs`), `.finger`, `.ripple`
and `polyline[opacity]` (hidden by `store_shots.mjs` for clean stills).

## The engine (`core.js`)

- Closed-form damped springs (no integration, so any `t` can be computed directly) with named
  presets: `R.camera`, `cameraFast`, `whip`, `text`, `soft`, `firm`, `pop`, `popFirm`, `slow`, `hit`,
  `edge`, `edgeSoft`, `app`. Leading and trailing edges on different springs make things stretch.
- Tracks of keyed values, `mixPoints` and `curve` for strokes, `applyVis` and `setStyle` that only
  touch the DOM when a value changes.
- `Odometer` (`build` / `set`): rolling digits with a locale number format (decimal comma, thousands
  dot by default; adapt it to the listing's locale). Check every change frame by frame.
- `cue(t, type, extra)`: registers a sound cue at the frame time.

## Android-specific craft

- **Phone frame**: a generic vector device (rounded body, camera hole), no maker branding. Only the
  real recording plays inside, chosen by `seek(t)` from `CLIPS`.
- **Touch indicators**: for each entry of `taps`, a soft disc that lands slightly before the touch
  and a Material ripple that spreads from it; swipes draw the disc along the path over `ms`.
- **Lifted elements**: a card leaving the screen starts as an exact crop of the current frame
  (same position and size), then crossfades with a short blur to a vector replica built from the
  app's theme. Calibrate the replica against the crop (`keyframe.py`, `rects.py`, `compare.py`,
  `diffpng.py`, `measure_boxes.py`). It always sits on an opaque surface with the app's radius,
  color and a soft shadow.
- **The vertical cut** is composed for 1080x1920 with the safe bands of `SKILL.md`, not cropped.

## Render

- Drafts: `video/scripts/draft.sh <16x9|9x16> <out.mp4> [duration]`, 30 fps at half scale, with the
  current mix (`video/audio/mix.wav`).
- Final: `video/scripts/final2.sh <16x9|9x16> <out.mp4> <mix.wav> ["00 01 03"]` renders segments in
  parallel (`segment.mjs`), 4 subframes per frame averaged with ffmpeg `tmix` at 60 fps, as many
  browsers as `resources.sh` says fit in free memory, each batch inside
  `systemd-run --user --scope -p MemoryMax=... -p MemorySwapMax=...`. The optional list re-renders
  only those segments. `final.sh` is the simpler single-pass version.
- `editor/gpu-test.mjs` tells whether Chromium renders faster on the GPU on your machine.
- Segment cuts, the 41 s length and similar constants in the scripts are example values from a past
  production: adapt them.

## Review material

- `sheet.mjs`: contact sheet of a folder of frames. `snap.mjs`: single frames at given times, every
  half beat (`--beats`) or from a list (`--list`).
- `clipsheet.py`, `clipstrip.py`: sheets and strips of a recording with its time written on each.
- `deliverables.sh <16x9|9x16> <final.mp4>`: one frame per second, key stills and a light preview
  (<= 14 MB) in `video/deliverables/`. It needs `video/film/assets/IBMPlexSans-Bold.ttf` (or edit the
  font path); `clipstrip.py` uses any `.ttf` in that folder.

## Known gaps

- `keyframe.py` expects `<material>/keyframes/` to exist: create it first.
- `draft.sh`, `final.sh` and `final2.sh` need `systemd-run --user` (systemd in WSL).
