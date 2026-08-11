#!/usr/bin/env python3
"""
360° -> panorámica PARCIAL para Kuula.

Recorta la equirectangular al ángulo que quieras e inyecta el metadato
GPano, para que Kuula limite el giro horizontal a la zona con imagen.

Instalación (una sola vez, sin Homebrew):
    pip3 install pillow

Uso:
    python3 360_a_parcial.py "/ruta/Insta360 Depto"
    python3 360_a_parcial.py "/ruta/Insta360 Depto" --fov 220
    python3 360_a_parcial.py "/ruta/Insta360 Depto" --fov 200 --rot 90
    python3 360_a_parcial.py "/ruta/Insta360 Depto" --fov 200 --rot 90 --solo 7.JPG

    --fov  grados a conservar (180 = mitad). Default 180.
    --rot  grados a girar ANTES de recortar. Sirve para elegir QUÉ parte
           se conserva, y así dejar afuera donde estabas parado.
    --solo procesar un solo archivo.

Las originales no se tocan: la salida va a una subcarpeta parcial-<fov>/
"""

import argparse
import struct
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Falta Pillow.  Instalalo con:  pip3 install pillow")

Image.MAX_IMAGE_PIXELS = None  # las equirect de 72 MP son enormes

XMP_NS = b"http://ns.adobe.com/xap/1.0/\x00"


def xmp_packet(crop_w, crop_h, full_w, full_h, left, top):
    """XMP con los tags GPano que Kuula usa para panorámicas parciales."""
    return f"""<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:GPano="http://ns.google.com/photos/1.0/panorama/"
    GPano:UsePanoramaViewer="True"
    GPano:ProjectionType="equirectangular"
    GPano:CroppedAreaImageWidthPixels="{crop_w}"
    GPano:CroppedAreaImageHeightPixels="{crop_h}"
    GPano:FullPanoWidthPixels="{full_w}"
    GPano:FullPanoHeightPixels="{full_h}"
    GPano:CroppedAreaLeftPixels="{left}"
    GPano:CroppedAreaTopPixels="{top}"/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>""".encode("utf-8")


def inject_xmp(jpeg_bytes, xmp):
    """Inserta un segmento APP1 con el XMP justo después del SOI."""
    if jpeg_bytes[:2] != b"\xff\xd8":
        raise ValueError("no parece un JPEG")
    payload = XMP_NS + xmp
    seg_len = len(payload) + 2
    if seg_len > 0xFFFF:
        raise ValueError("XMP demasiado grande para un solo APP1")
    segment = b"\xff\xe1" + struct.pack(">H", seg_len) + payload
    return jpeg_bytes[:2] + segment + jpeg_bytes[2:]


def procesar(src, out_dir, fov, rot):
    im = Image.open(src)
    W, H = im.size

    crop_w = int(W * fov / 360)
    left = (W - crop_w) // 2
    roll = int(W * rot / 360) % W

    # girar horizontalmente (wrap-around) para elegir qué parte se conserva
    if roll:
        izq = im.crop((roll, 0, W, H))
        der = im.crop((0, 0, roll, H))
        rolled = Image.new(im.mode, (W, H))
        rolled.paste(izq, (0, 0))
        rolled.paste(der, (W - roll, 0))
        im = rolled

    recorte = im.crop((left, 0, left + crop_w, H))

    dest = out_dir / src.name
    recorte.save(dest, "JPEG", quality=95, subsampling=0)

    data = dest.read_bytes()
    xmp = xmp_packet(crop_w, H, W, H, left, 0)
    dest.write_bytes(inject_xmp(data, xmp))

    return (W, H), (crop_w, H)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("carpeta", help="carpeta con las panorámicas originales")
    p.add_argument("--fov", type=int, default=180, help="grados a conservar (default 180)")
    p.add_argument("--rot", type=int, default=0, help="grados a girar antes de recortar")
    p.add_argument("--solo", help="procesar un solo archivo")
    a = p.parse_args()

    carpeta = Path(a.carpeta).expanduser()
    if not carpeta.is_dir():
        sys.exit(f"No existe la carpeta: {carpeta}")

    if a.solo:
        archivos = [carpeta / a.solo]
    else:
        archivos = sorted(
            f for f in carpeta.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg") and f.is_file()
        )

    if not archivos:
        sys.exit(f"No encontré JPGs en: {carpeta}")

    out_dir = carpeta / f"parcial-{a.fov}"
    out_dir.mkdir(exist_ok=True)

    print(f"FOV={a.fov}°  ROT={a.rot}°  ->  {out_dir}\n")
    for f in archivos:
        try:
            orig, nuevo = procesar(f, out_dir, a.fov, a.rot)
            print(f"  ✓ {f.name}  {orig[0]}x{orig[1]} -> {nuevo[0]}x{nuevo[1]}")
        except Exception as e:
            print(f"  ✗ {f.name}: {e}")

    print(f"\nListo. Archivos en: {out_dir}")


if __name__ == "__main__":
    main()
