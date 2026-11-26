#!/usr/bin/env bash
# Bygger den färdiga filmen: bilden i delar, ljudet, fullversionen, mobilversionen och ett kontaktark.
#   bash bygg.sh
# DEMOFILM_TEMP=<mapp> lägger Remotions och Chromes temporära filer där (på Antons dator: D:, C: är full).
set -uo pipefail
cd "$(dirname "$0")"
if [ -n "${DEMOFILM_TEMP:-}" ]; then export TEMP="$DEMOFILM_TEMP" TMP="$DEMOFILM_TEMP" TMPDIR="$DEMOFILM_TEMP"; fi
mkdir -p out

for f in $(node verktyg/tider.mjs --klipp); do
  [ -f "public/$f" ] || { echo "Klippet saknas: public/$f (se README)"; exit 1; }
done
VANTAT=$(node verktyg/tider.mjs --totalt)
LANGD=$(BARA_LANGD=1 node verktyg/render-parts.mjs | tail -1)
[ "$VANTAT" = "$LANGD" ] || { echo "tider.mjs säger $VANTAT rutor, Film.tsx $LANGD. Räkningarna måste vara lika."; exit 1; }

SIZE=500
PARTS=$(( (LANGD + SIZE - 1) / SIZE ))
rm -rf out/parts out/stum.mp4 out/ljud.wav out/snajp-demo.mp4 out/snajp-demo-mobil.mp4
for i in $(seq 1 "$PARTS"); do
  for forsok in 1 2 3 4; do
    if ONLY_PART=$i PART_SIZE=$SIZE node verktyg/render-parts.mjs > "out/render-$i.log" 2>&1; then break; fi
    echo "del $i, försök $forsok föll: $(grep -m1 -i error "out/render-$i.log" | cut -c1-120)"
  done
done
PART_SIZE=$SIZE node verktyg/render-parts.mjs > out/render-ihop.log 2>&1 || { echo "Ihopsättningen föll"; tail -5 out/render-ihop.log; exit 1; }

node verktyg/ljud.mjs || { echo "Ljudet föll"; exit 1; }
ffmpeg -v error -y -i out/stum.mp4 -i out/ljud.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart out/snajp-demo.mp4 || exit 1

# Mobilversionen ska under 30 MB, gränsen för att skicka en fil till mobilen.
for crf in 27 29 31; do
  ffmpeg -v error -y -i out/snajp-demo.mp4 -c:v libx264 -preset slow -crf $crf -pix_fmt yuv420p -c:a aac -b:a 128k -movflags +faststart out/snajp-demo-mobil.mp4 || exit 1
  [ "$(wc -c < out/snajp-demo-mobil.mp4)" -lt 30000000 ] && break
done

ffprobe -v error -count_frames -show_entries format=duration,size:stream=codec_name,nb_read_frames -of default=nw=1 out/snajp-demo.mp4
ffmpeg -v error -y -i out/snajp-demo.mp4 -vf "fps=1/4.72,scale=640:360,tile=5x6:padding=6:color=white" -frames:v 1 out/kontaktark.png
echo "klar: out/snajp-demo.mp4, out/snajp-demo-mobil.mp4, out/kontaktark.png"
