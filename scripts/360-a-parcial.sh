#!/bin/bash
# ---------------------------------------------------------------
# 360° -> panorámica PARCIAL para Kuula
#
# Recorta la equirectangular al ángulo que quieras y le inyecta el
# metadato GPano para que Kuula limite el giro horizontal a esa zona.
#
# Requiere (una sola vez):
#   brew install imagemagick exiftool
#
# Uso:
#   ./360-a-parcial.sh                 # 180°, centrado, todas
#   ./360-a-parcial.sh 220             # 220°, centrado, todas
#   ./360-a-parcial.sh 200 90          # 200°, girado 90°, todas
#   ./360-a-parcial.sh 200 90 5.JPG    # solo ese archivo
#
#   FOV = grados a conservar (180 = mitad)
#   ROT = cuántos grados girar ANTES de recortar. Sirve para elegir
#         QUÉ mitad se conserva (y dejar afuera donde estabas parado).
# ---------------------------------------------------------------

set -euo pipefail

# ⬇️ AJUSTÁ ESTA RUTA a donde estén las 25 originales
IN="$HOME/Desktop/Insta360 Depto"

FOV="${1:-180}"
ROT="${2:-0}"
SOLO="${3:-}"

OUT="$IN/parcial-${FOV}"
mkdir -p "$OUT"

command -v magick   >/dev/null || { echo "Falta ImageMagick: brew install imagemagick"; exit 1; }
command -v exiftool >/dev/null || { echo "Falta exiftool: brew install exiftool"; exit 1; }

if [[ -n "$SOLO" ]]; then
  archivos=("$IN/$SOLO")
else
  shopt -s nullglob nocaseglob
  archivos=("$IN"/*.jpg)
  shopt -u nocaseglob
fi

[[ ${#archivos[@]} -eq 0 ]] && { echo "No encontré JPGs en: $IN"; exit 1; }

echo "FOV=${FOV}°  ROT=${ROT}°  ->  $OUT"
echo

for f in "${archivos[@]}"; do
  base=$(basename "$f")

  W=$(magick identify -format "%w" "$f")
  H=$(magick identify -format "%h" "$f")

  CW=$(( W * FOV / 360 ))          # ancho recortado
  OFF=$(( (W - CW) / 2 ))          # offset centrado
  ROLL=$(( W * ROT / 360 ))        # giro previo

  magick "$f" -roll "+${ROLL}+0" -crop "${CW}x${H}+${OFF}+0" +repage "$OUT/$base"

  exiftool -overwrite_original -q \
    -XMP-GPano:UsePanoramaViewer=True \
    -XMP-GPano:ProjectionType=equirectangular \
    -XMP-GPano:CroppedAreaImageWidthPixels="$CW" \
    -XMP-GPano:CroppedAreaImageHeightPixels="$H" \
    -XMP-GPano:FullPanoWidthPixels="$W" \
    -XMP-GPano:FullPanoHeightPixels="$H" \
    -XMP-GPano:CroppedAreaLeftPixels="$OFF" \
    -XMP-GPano:CroppedAreaTopPixels=0 \
    "$OUT/$base"

  echo "  ✓ $base  (${W}x${H} -> ${CW}x${H})"
done

echo
echo "Listo. Archivos en: $OUT"
