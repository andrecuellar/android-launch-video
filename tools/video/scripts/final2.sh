#!/usr/bin/env bash
# Final render by segments: each segment is rendered (4 subframes) and encoded on its own with the same
# x264 parameters, and kept in video/render/<format>/. Then they are joined with -c copy and the audio
# is muxed in. That way a fix only re-renders the segments that change.
# Usage: final2.sh <16x9|9x16> <out.mp4> <mix.wav> [segments to redo, e.g. "00 01 03"; all by default]
set -euo pipefail
F=$1; OUT=$2; MIX=$3; ONLY=${4:-}
V=/PATH/TO/WORKDIR/video
FPS=60; SUB=4
R=$V/render/$F; mkdir -p $R
# Segment edges in frames (4 s), without cutting the logo entrance (35.6 to 36.6 s).
# Example values from a past production: adapt them to your film.
B=(0 240 480 720 960 1200 1440 1680 1920 2100 2280 2460)
read_res() { read -r WK MEM SW <<<"$($V/scripts/resources.sh | sed -E 's/workers=([0-9]+) memmax=([0-9A-Z]+) swapmax=([0-9A-Z]+).*/\1 \2 \3/')"; }
read_res; until [ "$WK" -ge 1 ]; do echo "no resources: waiting"; sleep 10; read_res; done
LIST=""
for ((i=0; i<${#B[@]}-1; i++)); do n=$(printf %02d $i); if [ -z "$ONLY" ] || [[ " $ONLY " == *" $n "* ]]; then LIST+="$n ${B[i]} ${B[i+1]}\n"; fi; done
echo "format $F: segments to redo: $(printf "$LIST" | awk '{printf "%s ", $1}')(workers $WK, MemoryMax=$MEM)"
cat > $R/.segment.sh <<EOS
#!/usr/bin/env bash
set -euo pipefail
n=\$1; a=\$2; b=\$3; T=$R/.sub-\$n
rm -rf \$T; mkdir -p \$T
node $V/scripts/segment.mjs $F 1 $FPS $SUB \$a \$b \$T
c=\$(ls \$T | wc -l); [ "\$c" -eq \$(( (b - a) * $SUB )) ] || { echo "segment \$n: missing subframes (\$c)"; exit 1; }
ffmpeg -loglevel error -y -framerate $((FPS * SUB)) -start_number \$(( a * $SUB )) -i "\$T/s%06d.jpg" \
  -filter_complex "[0:v]format=rgb24,tmix=frames=$SUB:weights='1 1 1 1',select='eq(mod(n\,$SUB)\,$((SUB - 1)))',setpts=N/($FPS*TB),scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]" \
  -map "[v]" -r $FPS -c:v libx264 -preset slow -tune film -crf 15 -g 120 -bf 3 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -an $R/seg-\$n.mp4
rm -rf \$T
echo "segment \$n done"
EOS
chmod +x $R/.segment.sh
printf "$LIST" | systemd-run --user --scope -p MemoryMax=$MEM -p MemorySwapMax=$SW --quiet xargs -P "$WK" -L 1 bash $R/.segment.sh
ls $R/seg-*.mp4 | sed "s|^|file '|; s|$|'|" > $R/list.txt
[ "$(wc -l < $R/list.txt)" -eq $((${#B[@]} - 1)) ] || { echo "missing segments"; exit 1; }
ffmpeg -loglevel error -y -f concat -safe 0 -i $R/list.txt -i "$MIX" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT"
echo "done: $OUT"
