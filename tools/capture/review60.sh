#!/usr/bin/env bash
# review60.sh <name> [every_s]: duration and contact sheet of a clips60/ clip (GPU capture).
V=/PATH/TO/WORKDIR/clips60/$1.mp4
R=/PATH/TO/WORKDIR/review
mkdir -p "$R"
every=${2:-1}
ffprobe -v error -show_entries format=duration:stream=width,height,nb_frames,avg_frame_rate -of default=nw=1 "$V"
ffmpeg -v error -y -i "$V" -vf "fps=1/$every,scale=216:480,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=16:fontcolor=red:box=1:boxcolor=white,tile=8x2:padding=4:color=black" -frames:v 1 "$R/60-$1-sheet.png" 2>&1 | tail -2
ls -la "$R/60-$1-sheet.png"
