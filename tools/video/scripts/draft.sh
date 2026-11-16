#!/usr/bin/env bash
# Draft in motion: 30 fps without subframes, scale 0.5, with the mix. Usage: draft.sh <16x9|9x16> <out.mp4> [duration=41]
set -euo pipefail
F=$1; OUT=$2
V=/PATH/TO/WORKDIR/video
DUR=${3:-41.0}; FPS=30; N=$(python3 -c "print(int(round($DUR*$FPS)))")
TMP=$V/draft/.frames-$F
rm -rf "$TMP"; mkdir -p "$TMP"
read -r WK MEM SW <<<"$($V/scripts/resources.sh | sed -E 's/workers=([0-9]+) memmax=([0-9A-Z]+) swapmax=([0-9A-Z]+).*/\1 \2 \3/')"
[ "$WK" -lt 1 ] && { echo "no resources: waiting"; until [ "$($V/scripts/resources.sh | sed -E 's/workers=([0-9]+).*/\1/')" -ge 1 ]; do sleep 5; done; WK=2; }
P=$(( WK > 4 ? 4 : WK ))   # two formats can run at once: each one uses 4 at most
echo "format $F: $N frames, $P workers, MemoryMax=$MEM"
CMD=""
for ((w=0; w<P; w++)); do
  a=$(( N * w / P )); b=$(( N * (w + 1) / P ))
  CMD+="node $V/scripts/segment.mjs $F 0.5 $FPS 1 $a $b $TMP & "
done
CMD+="wait"
systemd-run --user --scope -p MemoryMax=$MEM -p MemorySwapMax=$SW --quiet bash -c "$CMD"
n=$(ls "$TMP" | wc -l); [ "$n" -eq "$N" ] || { echo "missing frames: $n of $N"; exit 1; }
if [ "$F" = "9x16" ]; then SC=540:960; else SC=960:540; fi   # headless Chromium ignores the 0.5 scale: it is reduced here
ffmpeg -loglevel error -y -framerate $FPS -i "$TMP/s%06d.jpg" -i $V/audio/mix.wav \
  -map 0:v -map 1:a -vf "scale=$SC:flags=lanczos" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT"
rm -rf "$TMP"
echo "done: $OUT"
