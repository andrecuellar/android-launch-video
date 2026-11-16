#!/usr/bin/env bash
# Splits a master into 14 MB chunks (an Artifact file accepts up to 15 MB) and prints the JSON entry
# read by delivery/downloads/index.html. Chunks keep the .mp4 extension so the Artifact accepts them.
# Usage: split.sh <master.mp4> <parts_folder> ["Title"]
set -euo pipefail
m=$1; d=$2; title=${3:-$(basename "$m" .mp4)}
mkdir -p "$d"; b=$(basename "$m" .mp4)
rm -f "$d/$b"-??.mp4
split -b 14000000 -d -a 2 --additional-suffix=.mp4 "$m" "$d/$b-"
bytes=$(stat -c %s "$m"); sha=$(sha256sum "$m" | cut -d' ' -f1)
parts=$(cd "$d" && ls "$b"-??.mp4 | sed 's#^#"parts/#; s#$#"#' | paste -sd, -)
printf '{"id":"%s","title":"%s","file":"%s","bytes":%s,"sha256":"%s","parts":[%s]}\n' "$b" "$title" "$(basename "$m")" "$bytes" "$sha" "$parts"
