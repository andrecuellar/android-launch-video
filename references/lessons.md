# Lessons, as rules

Each rule below cost at least one redo. Hold them from the start.

## Capture

- `screenrecord` in the emulator caps at about 41 fps at 1080x2400. Do not plan a 60 fps film on it.
- Do not rebuild motion with animated screenshots "as a fallback". It reads fake at once; capture
  real 60 fps or change the scene.
- A locked Windows session delivers no frames to Desktop Duplication, and adb taps do not keep the
  session awake. Check the lock state and raise the screen timeout before every take.
- Emulator ports are global to the machine. Pick a free one; never reuse another session's.
- System animation scale at 0 makes the app move unlike a real phone. Keep it at 1.
- A take with stutter is recorded again. Interpolation shows.
- The tap time is the end of `adb shell input`, not its start: the command boots a VM first.

## Environment and data

- A seed through an admin SDK with one emulator variable missing writes to production. Check all
  of them before seeding.
- A local API with simulated providers can write invented data into a shared database. Count rows
  before and after any write to something shared.
- Telemetry left on in the recording build sends demo sessions to production dashboards.
- Personal data never appears, not even in a list that scrolls past in a few frames.

## Film

- Anything lifted off the phone needs its own opaque surface. A floating text or a card without
  background looks unfinished.
- The vertical cut is composed on its own. A crop of the 16:9 loses the brand and the safe bands.
- Rolling digits can show garbage values for one or two frames. Check them frame by frame.
- `seek(t)` must be pure. A cache that depends on the order of requests breaks parallel renders in
  ways that only show at segment joins.
- Long strokes that stretch and cross on the beat feel alive; rigid blocks feel like a template.
- Never add elements the brand or app does not have (play glyph, color wipes, text backgrounds).

## Music

- Some stock tracks hide chopped vocal hits that sound like words, sometimes rude ones. Listening
  once is not enough: fingerprint the hit and check every beat of the edit (threshold 0.88).
- Cuts on the beat with a short equal-power crossfade placed in the dip before the attack are
  inaudible. Anywhere else they click.
- An edit section can drag the echo of a removed hit: lower it, do not just cut the bar.

## Narration

- Free TTS quotas are small (a handful of generations per day). Log every request, never retry a
  429, and get the casting approved with short lines before generating the full take.
- The brand pronunciation goes in the director's notes of the prompt, never as on-screen text or a
  respelling in the transcript. Verify it with Whisper with and without a hint.
- The voice leads: place each line in its window and land its key word on the visual change it
  names. Stretching time beyond about 6 % is audible.
- The narrated cut is a separate master. Never overwrite the music-only cut.

## Review and delivery

- Never show anything that was not looked at first, at real size and in context.
- The reviewer often watches on a phone: keep previews under 14 MB and deliver through a page
  that works on mobile.
- Large files fail silently when split wrong. Verify the reassembled master with SHA-256.
- Restore the monitor, the screen timeout and every temporary setting even when something fails.
