#!/usr/bin/env python3
"""
exif_gps.py - Extrae metadatos EXIF (fecha, equipo, GPS) de fotos JPEG.

Requiere Pillow:  pip install pillow
Uso:
  python3 exif_gps.py CARPETA_O_FOTO [--csv salida.csv]

Para cada foto muestra: fabricante/modelo, fecha original, fecha de modificación,
coordenadas en grados decimales y un link a Google Maps.
Recordá: la fecha EXIF la escribe el equipo y se puede editar. Contrastala siempre
con otras fuentes (nombre del archivo, base de datos de la galería, chats).
"""
import argparse
import csv
from pathlib import Path

from PIL import Image

TAGS = {0x010F: "fabricante", 0x0110: "modelo", 0x0132: "fecha_modificacion", 0x0131: "software"}
EXIF_IFD, GPS_IFD = 0x8769, 0x8825


def a_decimal(dms, ref):
    g, m, s = (float(x) for x in dms)
    v = g + m / 60 + s / 3600
    return -v if ref in ("S", "W") else v


def leer(ruta: Path):
    d = {"archivo": ruta.name}
    with Image.open(ruta) as img:
        ex = img.getexif()
        for tag, nombre in TAGS.items():
            if tag in ex:
                d[nombre] = str(ex[tag]).strip()
        sub = ex.get_ifd(EXIF_IFD)
        d["fecha_original"] = sub.get(0x9003, "")
        gps = ex.get_ifd(GPS_IFD)
        if 2 in gps and 4 in gps:
            lat = a_decimal(gps[2], gps.get(1, "N"))
            lon = a_decimal(gps[4], gps.get(3, "E"))
            d["lat"], d["lon"] = round(lat, 6), round(lon, 6)
            d["mapa"] = f"https://maps.google.com/?q={lat:.6f},{lon:.6f}"
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ruta", type=Path)
    ap.add_argument("--csv")
    a = ap.parse_args()
    fotos = [a.ruta] if a.ruta.is_file() else sorted(
        p for p in a.ruta.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg"))
    filas = []
    for f in fotos:
        try:
            d = leer(f)
        except Exception as e:  # archivo dañado o no es imagen
            d = {"archivo": f.name, "error": str(e)}
        filas.append(d)
        print(f"\n{d['archivo']}")
        for k, v in d.items():
            if k != "archivo":
                print(f"   {k:<20} {v}")
        if "lat" not in d and "error" not in d:
            print("   (sin GPS)")
    if a.csv:
        campos = sorted({k for f in filas for k in f}, key=lambda k: (k != "archivo", k))
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=campos); w.writeheader(); w.writerows(filas)
        print(f"\nCSV: {a.csv}")


if __name__ == "__main__":
    main()
