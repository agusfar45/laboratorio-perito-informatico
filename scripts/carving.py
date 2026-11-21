#!/usr/bin/env python3
"""
carving.py - File carving por firmas (header/footer) sobre una imagen cruda (.dd/.raw/.img).

Sirve cuando el sistema de archivos fue borrado o formateado: no hay nombres ni
carpetas, pero los bytes de los archivos siguen en el disco. Buscamos las "firmas
mágicas" de inicio y fin de cada tipo de archivo y recortamos lo que hay en medio.

Uso:
  python3 carving.py imagen.dd -o recuperados/

Es la misma idea que usan Foremost, Scalpel o PhotoRec (versiones mucho más completas).
Cada archivo recuperado sale con su offset y su SHA-256 para el informe.
"""
import argparse
import hashlib
from pathlib import Path

# tipo: (header, footer, bytes extra después del footer, tamaño máximo)
FIRMAS = {
    "jpg": (b"\xff\xd8\xff", b"\xff\xd9", 2, 10 * 1024 * 1024),
    "png": (b"\x89PNG\r\n\x1a\n", b"IEND\xaeB`\x82", 8, 20 * 1024 * 1024),
    "pdf": (b"%PDF-", b"%%EOF", 5, 50 * 1024 * 1024),
}


def main():
    import sys
    if hasattr(sys.stdout, "reconfigure"):  # la consola de Windows (cp1252) no imprime "→" ni emojis
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("imagen", type=Path)
    ap.add_argument("-o", "--salida", type=Path, default=Path("recuperados"))
    a = ap.parse_args()

    datos = a.imagen.read_bytes()  # para imágenes grandes habría que leer por bloques (mmap)
    a.salida.mkdir(parents=True, exist_ok=True)
    print(f"Imagen: {a.imagen} ({len(datos):,} bytes)\n")
    n = 0
    for tipo, (head, foot, extra, maximo) in FIRMAS.items():
        pos = datos.find(head)
        while pos != -1:
            fin = datos.find(foot, pos + len(head), pos + maximo)
            n += 1
            if fin == -1:
                # fragmento: tiene inicio pero no fin (archivo sobrescrito en parte)
                blob, estado = datos[pos:pos + 64 * 1024], "INCOMPLETO (sin footer)"
            else:
                blob, estado = datos[pos:fin + extra], "completo"
            nombre = f"{n:03d}_off{pos:08X}.{tipo}"
            (a.salida / nombre).write_bytes(blob)
            print(f"{nombre:<26} {len(blob):>9,} B  {estado:<24} sha256={hashlib.sha256(blob).hexdigest()[:16]}…")
            pos = datos.find(head, pos + (len(blob) if fin != -1 else len(head)))
    print(f"\n{n} archivo(s) recuperado(s) en {a.salida}/")


if __name__ == "__main__":
    main()
