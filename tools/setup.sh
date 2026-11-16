#!/usr/bin/env bash
# Creates a work dir for one production from these tools.
#
# Usage: tools/setup.sh <work-dir> [--skip-install]
#
# 1. Copies every tool into <work-dir> (the work dir must not exist or be empty).
# 2. Replaces the path placeholder with the absolute work dir in every file.
# 3. Creates config.json from config.example.json (edit it before capturing).
# 4. Unless --skip-install: creates <work-dir>/venv with requirements.txt, runs npm install in
#    <work-dir>/editor and installs the Chromium build that playwright-core 1.48.2 expects.
# The Whisper model is not downloaded here (about 3 GB): see references/narration.md.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <work-dir> [--skip-install]" >&2
  exit 2
fi
SRC=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$1"
T=$(cd "$1" && pwd)
SKIP=${2:-}

if [ -n "$(ls -A "$T" 2>/dev/null)" ]; then
  echo "error: $T is not empty" >&2
  exit 1
fi

# Built from two halves so this script never matches its own replacement.
PLACEHOLDER="/PATH/TO/""WORKDIR"

echo "copying tools to $T"
(cd "$SRC" && tar --exclude=./setup.sh --exclude=./node_modules --exclude='./editor/node_modules' \
  --exclude='*/__pycache__' --exclude=./config.json -cf - .) | (cd "$T" && tar -xf -)

echo "replacing the placeholder with $T"
grep -rlF "$PLACEHOLDER" "$T" | while read -r f; do
  sed -i "s#${PLACEHOLDER}#${T}#g" "$f"
done
if grep -rqF "$PLACEHOLDER" "$T"; then
  echo "error: placeholder left in:" >&2
  grep -rlF "$PLACEHOLDER" "$T" >&2
  exit 1
fi

cp "$T/config.example.json" "$T/config.json"
mkdir -p "$T/clips" "$T/clips60" "$T/tests60" "$T/review" "$T/models"
find "$T" -name '*.sh' -exec chmod +x {} +

if [ "$SKIP" = "--skip-install" ]; then
  echo "skipped the Python and Node installs"
else
  echo "creating the Python venv"
  python3 -m venv "$T/venv"
  "$T/venv/bin/pip" install --quiet --upgrade pip
  "$T/venv/bin/pip" install --quiet -r "$T/requirements.txt"
  echo "installing playwright-core"
  (cd "$T/editor" && npm install --silent)
  echo "installing the Chromium build for playwright-core 1.48.2"
  (cd "$T/editor" && npx --yes playwright@1.48.2 install chromium)
fi

cat <<MSG

Work dir ready: $T
Next:
  1. Edit $T/config.json (emulator serial, Windows paths, screen corner, encoder).
  2. Download the Whisper model into $T/models/faster-whisper-large-v3 (references/narration.md).
  3. Export GEMINI_API_KEY in your shell before narration (never write it to a file in the work dir).
MSG
