#!/usr/bin/env python3
"""
carving.py - File carving por firmas (header/footer) sobre una imagen cruda (.dd/.raw/.img).

Sirve cuando el sistema de archivos fue borrado o formateado: no hay nombres ni
carpetas, pero los bytes de los archivos siguen en el disco. Buscamos las "firmas
mágicas" de inicio y fin de cada tipo de archivo y recortamos lo que hay en medio.

Tipos: JPG, PNG, PDF y ZIP (incluye DOCX / XLSX / PPTX, que son ZIP por dentro).

Uso:
  python3 carving.py imagen.dd -o recuperados/

Es la misma idea que usan Foremost, Scalpel o PhotoRec (versiones mucho más completas).
Cada archivo recuperado sale con su offset y su SHA-256 para el informe.
"""
import argparse
import hashlib
import io
import struct
import zipfile
from pathlib import Path


def fin_zip(datos, pos_footer):
    """El ZIP termina en el registro EOCD: 22 bytes fijos + un comentario de largo variable
    (los 2 bytes del offset 20 del EOCD dicen cuánto mide)."""
    if pos_footer + 22 > len(datos):
        return len(datos)
    largo_comentario = struct.unpack_from("<H", datos, pos_footer + 20)[0]
    return pos_footer + 22 + largo_comentario


# tipo: (header, footer, bytes extra después del footer — número o función —, tamaño máximo)
FIRMAS = {
    "jpg": (b"\xff\xd8\xff", b"\xff\xd9", 2, 10 * 1024 * 1024),
    "png": (b"\x89PNG\r\n\x1a\n", b"IEND\xaeB`\x82", 8, 20 * 1024 * 1024),
    "pdf": (b"%PDF-", b"%%EOF", 5, 50 * 1024 * 1024),
    "zip": (b"PK\x03\x04", b"PK\x05\x06", fin_zip, 50 * 1024 * 1024),
}


def subtipo_zip(blob):
    """DOCX/XLSX/PPTX son ZIP: se distinguen por las carpetas que traen adentro.
    Los nombres de cada archivo interno están en texto plano en los local headers."""
    if b"[Content_Types].xml" in blob:
        for carpeta, ext in ((b"word/", "docx"), (b"xl/", "xlsx"), (b"ppt/", "pptx")):
            if carpeta in blob:
                return ext
    return "zip"


def validar_zip(blob):
    """Abre el ZIP y comprueba el CRC-32 de cada archivo interno."""
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            malo = z.testzip()
            return f"CRC OK, {len(z.namelist())} archivos internos" if malo is None else f"CRC MAL en {malo}"
    except zipfile.BadZipFile as ex:
        return f"no abre: {ex}"


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
                corte = extra(datos, fin) if callable(extra) else fin + extra
                blob, estado = datos[pos:corte], "completo"
            ext, nota = tipo, ""
            if tipo == "zip":
                ext = subtipo_zip(blob)
                nota = f"  [{validar_zip(blob)}]"
            nombre = f"{n:03d}_off{pos:08X}.{ext}"
            (a.salida / nombre).write_bytes(blob)
            print(f"{nombre:<26} {len(blob):>9,} B  {estado:<24} sha256={hashlib.sha256(blob).hexdigest()[:16]}…{nota}")
            # Completo: saltar el archivo entero (un DOCX tiene un "PK\x03\x04" por cada archivo
            # interno y no queremos recuperarlos sueltos). Incompleto: seguir desde el byte
            # siguiente, porque lo que lo sobrescribió puede ser otro archivo.
            pos = datos.find(head, pos + (len(blob) if fin != -1 else len(head)))
    print(f"\n{n} archivo(s) recuperado(s) en {a.salida}/")


if __name__ == "__main__":
    main()
