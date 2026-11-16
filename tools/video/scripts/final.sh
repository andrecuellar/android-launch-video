#!/usr/bin/env bash
# Final render: 60 fps with 4 averaged subframes (tmix), x264 crf 15, BT.709, AAC 48 kHz.
# Usage: final.sh <16x9|9x16> <out.mp4> <mix.wav>
set -euo pipefail
F=$1; OUT=$2; MIX=$3
V=/PATH/TO/WORKDIR/video
FPS=60; SUB=4; N=2460                       # 41.0 s (example length from a past production: adapt it)
TMP=$V/draft/.final-$F
mkdir -p "$TMP"
read_res() { read -r WK MEM SW <<<"$($V/scripts/resources.sh | sed -E 's/workers=([0-9]+) memmax=([0-9A-Z]+) swapmax=([0-9A-Z]+).*/\1 \2 \3/')"; }
read_res; until [ "$WK" -ge 1 ]; do echo "no resources: waiting"; sleep 10; read_res; done
# Segments: none of them cuts the logo entrance (35.6 to 36.6 s, frames 2136 to 2196).
# Example values from a past production: adapt them to your film.
if [ "$WK" -ge 8 ]; then CUTS="0 300 600 900 1200 1500 1800 2100 2460"; else CUTS="0 600 1200 1800 2460"; fi
set -- $CUTS; PAIRS=(); prev=$1; shift; for c in "$@"; do PAIRS+=("$prev $c"); prev=$c; done
echo "format $F: $N frames x $SUB subframes, ${#PAIRS[@]} segments, MemoryMax=$MEM"
CMD=""; for p in "${PAIRS[@]}"; do CMD+="node $V/scripts/segment.mjs $F 1 $FPS $SUB $p $TMP & "; done; CMD+="wait"
systemd-run --user --scope -p MemoryMax=$MEM -p MemorySwapMax=$SW --quiet bash -c "$CMD"
n=$(ls "$TMP" | wc -l); [ "$n" -eq $((N * SUB)) ] || { echo "missing subframes: $n of $((N * SUB))"; exit 1; }
ffmpeg -loglevel error -y -framerate $((FPS * SUB)) -i "$TMP/s%06d.jpg" -i "$MIX" \
  -filter_complex "[0:v]format=rgb24,tmix=frames=$SUB:weights='1 1 1 1',select='eq(mod(n\,$SUB)\,$((SUB - 1)))',setpts=N/($FPS*TB),scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]" \
  -map "[v]" -map 1:a -r $FPS -c:v libx264 -preset slow -tune film -crf 15 -g 120 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT"
rm -rf "$TMP"
echo "done: $OUT"
