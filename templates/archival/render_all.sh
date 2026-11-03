#!/bin/bash
# Template: templates/archival/render_all.sh (copied by `doc.py plan JOB`).
# Render every JS scene and map of this film (skips ones newer than their source), 3 at a time, each with a hard timeout,
# plus the subscribe overlay in the film's language. Run after `plan.py durations`, `scenes/src/build.py`, `maps/write_maps.py`.
P=$(cd "$(dirname "$0")" && (pwd -W 2>/dev/null || pwd)); R="$P/../.."  # pwd -W: Windows python reads brief.json below
cd "$R"
LANG_=$(.venv/Scripts/python.exe -c "import json;print(json.load(open('$P/brief.json',encoding='utf-8')).get('language','en'))")
jobs() {
  for js in "$P"/scenes/*.js; do n=$(basename "$js" .js); out="$P/media/scene-$n.mp4"
    [ -f "$out" ] && [ "$out" -nt "$js" ] && continue; echo "scene|$js|$out"; done
  for js in "$P"/maps/m-*.json; do n=$(basename "$js" .json); out="$P/media/map-$n.mp4"
    [ -f "$out" ] && [ "$out" -nt "$js" ] && continue; echo "map|$js|$out"; done
}
jobs | xargs -P 3 -I{} bash -c 'IFS="|" read k src out <<< "{}"
  if [ "$k" = scene ]; then timeout 600 node scripts/jsscene.mjs "$src" "$out" > /dev/null 2>&1 || echo "FAIL $src"
  else timeout 900 node scripts/mapscene.mjs "$src" "$out" > /dev/null 2>&1 || echo "FAIL $src"; fi; echo "done $(basename "$out")"'
[ -f "$P/media/scene-subscribe.mov" ] || timeout 600 node scripts/jsscene.mjs scenes/subscribe.js "$P/media/scene-subscribe.mov" --alpha --lang "$LANG_" > /dev/null 2>&1 || echo "FAIL subscribe"
echo DONE
