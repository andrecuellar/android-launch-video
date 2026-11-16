#!/usr/bin/env bash
# One-frame-per-second storyboard, key stills and a light preview of a final MP4.
# Usage: deliverables.sh <16x9|9x16> <final.mp4>
set -euo pipefail
F=$1; MP4=$2
V=/PATH/TO/WORKDIR/video
E=$V/deliverables; mkdir -p $E/stills
FONT=$V/film/assets/IBMPlexSans-Bold.ttf
if [ "$F" = "9x16" ]; then THUMB=216:384; COLS=11; PREV=720:1280; else THUMB=384:216; COLS=7; PREV=1280:720; fi
# storyboard: one frame in the middle of every second, with its time (41 = film length in seconds,
# an example value from a past production: adapt it)
ffmpeg -loglevel error -y -i "$MP4" -vf "select='gte(n\,30)*not(mod(n-30\,60))',scale=$THUMB,drawtext=fontfile=$FONT:text='%{eif\:t-0.5\:d}s':x=8:y=8:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55,tile=${COLS}x$(( (41 + COLS - 1) / COLS )):padding=6:color=0x1b1f1d" \
  -vsync vfr -frames:v 1 $E/storyboard-1fps-$F.png
# key stills (full frame); the times are example values from a past production: adapt them
for t in 3.5 4.9 6.6 13.3 19.35 21.0 25.3 26.6 31.9 34.9 39.5; do
  ffmpeg -loglevel error -y -ss $t -i "$MP4" -frames:v 1 $E/stills/$F-t$(printf %05.2f $t).png
done
# light preview: 720p, 30 fps, two passes at ~2.4 Mb/s (+ AAC 128k) to stay under 14 MB
P=$E/preview-$F.mp4; LOG=$V/draft/.pass-$F
ffmpeg -loglevel error -y -i "$MP4" -vf "scale=$PREV:flags=lanczos,fps=30" -c:v libx264 -preset slow -b:v 2400k -maxrate 3600k -bufsize 4800k -pass 1 -passlogfile $LOG -an -f mp4 /dev/null
ffmpeg -loglevel error -y -i "$MP4" -vf "scale=$PREV:flags=lanczos,fps=30" -c:v libx264 -preset slow -b:v 2400k -maxrate 3600k -bufsize 4800k -pass 2 -passlogfile $LOG \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -c:a aac -b:a 128k -ar 48000 -movflags +faststart "$P"
rm -f $LOG*
ls -la $E/storyboard-1fps-$F.png "$P" | awk '{print $5, $9}'
